from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db, bcrypt
from app.auth import auth
from app.auth.forms import RegistrationForm, LoginForm
from app.models import User, LearningProgress


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip(),
            email=form.email.data.strip().lower(),
            password_hash=hashed_pw
        )
        db.session.add(user)
        db.session.commit()

        # Log registration activity
        progress = LearningProgress(
            user_id=user.id,
            activity_type='account_created',
            activity_detail='Welcome to StudyMate AI!'
        )
        db.session.add(progress)
        db.session.commit()

        flash('Account created successfully! Welcome to StudyMate AI. Please sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form, title='Create Account')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html', form=form, title='Sign In')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('auth.login'))

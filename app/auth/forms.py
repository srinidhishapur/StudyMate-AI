from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                 ValidationError, Regexp)
from app.models import User


class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name',
                            validators=[DataRequired(), Length(min=2, max=128)])
    username = StringField('Username',
                           validators=[
                               DataRequired(),
                               Length(min=3, max=64),
                               Regexp(r'^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                      'Username must start with a letter and contain only '
                                      'letters, numbers, dots or underscores.')
                           ])
    email = StringField('Email Address',
                        validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password',
                             validators=[
                                 DataRequired(),
                                 Length(min=8, message='Password must be at least 8 characters.')
                             ])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(),
                                                 EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class LoginForm(FlaskForm):
    email = StringField('Email Address',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password',
                             validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

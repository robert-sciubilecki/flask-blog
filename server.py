import os

from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from wtforms import StringField, PasswordField, TextAreaField, EmailField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email
import datetime as dt
from functions import send_email, make_json
from secrets import token_hex
from flask_ckeditor import CKEditor, CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import Markup
from functools import wraps
import pyodbc
from sqlalchemy import create_engine
import urllib
from urllib.parse import quote_plus



year = dt.datetime.now().year
app = Flask(__name__)
app.secret_key = token_hex(16)
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER')
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI')
# db = pyodbc.connect(app.config['SQLALCHEMY_DATABASE_URI'])

server = "blog-sciu-server.database.windows.net"
database = "posts"
username = os.environ.get('USERNAME_DB')
password = os.environ.get('PASSWORD_DB')
driver = '{ODBC Driver 18 for SQL Server}'  # Use ODBC Driver 17 for SQL Server

# Create the connection string
odbc_str = 'Driver={ODBC Driver 18 for SQL Server};Server='+server+',1433;Database=posts;Uid=robert.sciu.admin;Pwd='+password+';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
connect_str = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(odbc_str)

# Create a SQLAlchemy database instance and initialize it with the Flask app


# Create a SQLAlchemy engine for executing SQL queries
# connection = pyodbc.connect(connect_str)

engine = create_engine(connect_str)


db = SQLAlchemy(app)
ckeditor = CKEditor(app)

API_KEY = os.environ.get('API_KEY')

# Flask SQLAlchemy database models /////////////////////////////////////////////////////////////////////////////


class PostsDb(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(500), nullable=True)
    user = relationship('UsersDb', back_populates='posts')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = relationship('CommentsDb', back_populates='post')


class CommentsDb(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    user = relationship('UsersDb', back_populates='comments')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post = relationship('PostsDb', back_populates='comments')
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    date = db.Column(db.String(100), nullable=False)


class UsersDb(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    username = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    posts = db.relationship('PostsDb', back_populates='user')
    comments = db.relationship('CommentsDb', back_populates='user')
    role = db.Column(db.String(10), default='user')

    def __init__(self, username, email, role='user'):
        self.username = username
        self.email = email
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

    def set_password(self, password):
        self.password = generate_password_hash(password, salt_length=10)

    def check_password(self, password):
        return check_password_hash(self.password, password)


with app.app_context():
    db.create_all()


# Flask Login //////////////////////////////////////////////////////////////////////////////////////////////

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(UsersDb).where(UsersDb.id == user_id)).scalar()

# Context Processors /////////////////////////////////////////////////////////////////////////////////////////////////

# def load_data():
#     with app.app_context():
#         posts_data = db.session.execute(db.select(PostsDb).order_by(PostsDb.id)).scalars()
#         posts_data = [post for post in posts_data]
#         return posts_data


# @app.context_processor
# def posts_data_context_processor():
#     posts = load_data()
#     return {'posts': posts}


# Flask Forms ///////////////////////////////////////////////////////////////////////////////////////////////////


class CommentForm(FlaskForm):
    class Meta:
        csrf_field_name = 'csrf_token_comment'
    text = TextAreaField(label='Comment', validators=[DataRequired()])
    submit = SubmitField(label='Submit', id='submit')


class ContactForm(FlaskForm):
    class Meta:
        csrf_field_name = 'csrf_token_contact'
    name = StringField(label='Name', validators=[DataRequired()])
    email = EmailField(label='Email', validators=[DataRequired(), Email()])
    message = TextAreaField(label='Message', validators=[DataRequired()])
    submit = SubmitField(label='Send', id='submit')


# Custom Validators //////////////////////////////////

def no_username(form, field):
    user = UsersDb.query.filter_by(username=field.data).first()
    if not user:
        message = 'Username does not exist. <a class="inline-link" href="/signup">Sign up</a>.'
        raise ValidationError(Markup(message))


def wrong_password(form, field):
    user = UsersDb.query.filter_by(username=form.username.data).first()
    if not user:
        return
    if not user.check_password(field.data):
        raise ValidationError('Wrong password.')

# //////////////////////////////////////////////////////


class LoginForm(FlaskForm):
    class Meta:
        csrf_field_name = 'csrf_token_login'
    username = StringField('Username', validators=[DataRequired(), no_username])
    password = PasswordField('Password', validators=[DataRequired(), wrong_password])
    submit = SubmitField(label='Login', id='login')


#CUSTOM VALIDATORS ////////////////////////////////


def unique_username(form, field):
    user = UsersDb.query.filter_by(username=field.data).first()
    if user:
        message = 'Username already exists. <a class="inline-link" href="/login">Login</a>.'
        raise ValidationError(Markup(message))


def unique_email(form, field):
    user = UsersDb.query.filter_by(email=field.data).first()
    if user:
        message = 'Email address is already registered. <a class="inline-link" href="/login">Login</a>.'
        raise ValidationError(Markup(message))

# ////////////////////////////////////////////////


class SignupForm(FlaskForm):
    class Meta:
        csrf_field_name = 'csrf_token_signup'
    username = StringField('Username', id='signup-username', validators=[DataRequired(), unique_username])
    email = EmailField('Email', validators=[DataRequired(), Email(), unique_email])
    password = PasswordField('Password', id='signup-password', validators=[DataRequired()])
    submit = SubmitField(label='Sign up', id='signup')


class NewPostForm(FlaskForm):
    class Meta:
        csrf_field_name = 'csrf_token_new_post'
    title = StringField('Title', validators=[DataRequired()])
    subtitle = StringField('Subtitle', validators=[DataRequired()])
    body = CKEditorField('Body', validators=[DataRequired()])
    # user = StringField('User', validators=[DataRequired()])
    background_img = FileField('Background image', validators=[FileAllowed(['webp', 'png'])])
    submit = SubmitField(label='Create post', id='create_post')


# CUSTOM DECORATORS ////////////////////////////////////////////////////////////////////////////////////////////////

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_admin():
            return f(*args, **kwargs)
        return abort(403)
    return decorated_function


# API //////////////////////////////////////////////////////////////////////////////////////////////////////////////


@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts_db_data = db.session.execute(db.select(PostsDb).order_by(PostsDb.id)).scalars()
    json_posts_db_data = [make_json(post) for post in posts_db_data]
    return jsonify(json_posts_db_data)


@app.route('/api/create_post', methods=['GET', 'POST'])
def create_post():
    api_key = request.args.get('api_key')
    if api_key != API_KEY:
        return jsonify({'status': 'error, invalid api key'})
    title = request.args.get('title')
    subtitle = request.args.get('subtitle')
    user = request.args.get('user')
    date = dt.datetime.now().date()
    body = request.args.get('body')
    with app.app_context():
        post = PostsDb(title=title, subtitle=subtitle, user=user, date=date, body=body)
        db.session.add(post)
        db.session.commit()
        return jsonify({'status': 'success'})


@app.route('/api/find_posts', methods=['GET'])
def find_posts():
    post_id = request.args.get('id')
    title = request.args.get('title')
    date = request.args.get('date')
    if post_id:
        post_data = db.session.execute(db.select(PostsDb).filter_by(id=post_id)).scalar()
        return make_json(post_data)
    elif title:
        posts_data = db.session.execute(db.select(PostsDb).filter_by(title=title)).scalars()
        return {post.id: make_json(post) for post in posts_data}
    elif date:
        post_data = db.session.execute(db.select(PostsDb).filter_by(date=date)).scalars()
        return {post.id: make_json(post) for post in post_data}


@app.route('/api/delete_post', methods=['GET', 'DELETE'])
def delete_post():
    api_key = request.args.get('api_key')
    if api_key != API_KEY:
        return jsonify({'status': 'error, invalid api key'})
    post_id = request.args.get('id')
    post = db.get_or_404(PostsDb, post_id)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'status': 'success'})

# Flask Routes /////////////////////////////////////////////////////////////////////////////////////////////////////


# def find_post(post_list, post_id):
#     matching_post = [post for post in post_list if post['id'] == post_id]
#     return matching_post[0]


@app.route("/")
def home():
    posts = db.session.execute(db.select(PostsDb)).scalars()
    posts = [post for post in posts][::-1]
    return render_template("index.html", posts=posts)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    post = db.get_or_404(PostsDb, post_id)
    post_id = str(post.id)
    date = dt.datetime.now().date()
    comment_form = CommentForm()
    comments = db.session.execute(db.select(CommentsDb).where(CommentsDb.post_id == post_id)).scalars()
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            comment = CommentsDb(text=comment_form.text.data, user_id=current_user.id, post_id=post_id, date=date)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash('You must be logged in to comment.')
            return redirect(url_for('show_post', post_id=post_id))
    return render_template("post.html", post=post, post_id=post_id, comment_form=comment_form, comments=comments)


@app.route('/new-post', methods=['GET', 'POST'])
@admin_only
def new_post():
    form = NewPostForm()
    if form.validate_on_submit():
        title = form.title.data
        subtitle = form.subtitle.data
        # user = form.user.data
        body = form.body.data
        date = dt.datetime.now().date()
        background_img = form.background_img.data
        with app.app_context():
            post = PostsDb(title=title,
                           subtitle=subtitle,
                           date=date,
                           body=body,
                           user=UsersDb.query.get(current_user.id),
                           user_id=current_user.id)
            db.session.add(post)
            db.session.commit()
            background_img_filename = f"{post.id}.{background_img.filename.rsplit('.')[-1].lower()}"
            background_img.save(os.path.join(app.config['UPLOAD_FOLDER'], background_img_filename))
            return redirect(url_for('show_post', post_id=post.id))
    return render_template("new-post.html", success=False, form=form)


@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = db.get_or_404(PostsDb, post_id)
    edit_form = NewPostForm(
        title=post.title,
        subtitle=post.subtitle,
        body=post.body,
        user=post.user,
        user_id=current_user.id
    )
    edit_form.submit.label.text = 'Update Post'

    if edit_form.validate_on_submit():
        post_to_update = db.get_or_404(PostsDb, post_id)
        post_to_update.title = edit_form.title.data
        post_to_update.subtitle = edit_form.subtitle.data
        post_to_update.body = edit_form.body.data
        # post_to_update.user = UsersDb.query.filter_by(username=edit_form.user.data).first()
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("new-post.html", form=edit_form, editing=True, post=post)


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/contact', methods=['GET', 'POST'])
def show_contact():
    form = ContactForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        message = form.message.data
        send_email(name, email, message)
        return render_template('contact.html', success=True, form=form)
    return render_template("contact.html", success=False, form=form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    signup_form = SignupForm()
    if signup_form.validate_on_submit():
        username = signup_form.username.data
        email = signup_form.email.data
        user = UsersDb(username=username, email=email)
        user.set_password(signup_form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('logged_in'))
    return render_template("signup.html", success=False, signup_form=signup_form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        username = login_form.username.data
        password = login_form.password.data
        user = db.session.execute(db.select(UsersDb).where(UsersDb.username == username)).scalar()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('logged_in'))

    return render_template("login.html", login_form=login_form)


@app.route('/logged-in')
def logged_in():
    return render_template("logged-in.html")


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


# if __name__ == "__main__":
#     app.run(debug=False)

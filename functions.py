import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


def send_email(sender_name, sender_email, message):
    from_email = os.environ.get('FROM_EMAIL')
    to_email = os.environ.get('TO_EMAIL')
    password = os.environ.get('PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = f'Form Submission from {sender_name}: {sender_email}'

    msg.attach(MIMEText(message, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            print('Email sent successfully!')
    except Exception as e:
        print('Email not sent:', str(e))


def make_json(post):
    post_json = {
        "title": post.title,
        "subtitle": post.subtitle,
        "body": post.body,
        "id": post.id,
        'date': post.date,
        'background_img': post.background_img,
        'alt': post.alt,
        'user': {
            'id': post.user.id,
            'username': post.user.username,
            },
        }
    return post_json
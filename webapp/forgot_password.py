import string
import smtplib
import random
import subprocess
import configparser
from email.mime.text import MIMEText
from flask import Flask, render_template, request
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

application = Flask(__name__)

@application.route("/", methods=['GET'])
def index():
    if request.args.get('code'):
        unlock_code = request.args.get('code')
        # unlock, new password
        re = s.query(RecoveryEmail).filter(RecoveryEmail.password_code==unlock_code).one_or_none()
        if re:
            jid = re.jid
            re.password_code = None
            s.merge(re)
            s.commit()
            # set new password and send email
            email_address = re.email
            password = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(10))
            p = subprocess.Popen(['/usr/bin/prosodyctl', 'passwd', jid], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
            args = bytes("%s\n%s\n" % (password, password), encoding='utf8')
            p.communicate(args)
            sendMail(email_address, 'new password', password)
            content = render_template('success.html', message='password was sent')
        else:
            content = render_template('error.html', message='link invalid')
    else:
        content = render_template('index.html')
    return content

@application.route("/", methods=['POST'])
def request_password():
    jid = request.form.get('jid')
    re = s.query(RecoveryEmail).filter(RecoveryEmail.jid==jid, RecoveryEmail.confirmed==True).one_or_none()
    if re:
        password_code = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(64))
        re.password_code = password_code
        s.merge(re)
        s.commit()
        password_code_link = 'https://www.pimux.de/password/?code=%s' % password_code
        sendMail(re.email, 'password reset request', 'click here: %s' % password_code_link)
        content = render_template('success.html', message='link was sent')
    else:
        content = render_template('error.html', message='user not found')
    return content


def sendMail(to, subject, message):
    sender = 'pimux@pimux.de'
    msg = MIMEText(message, 'plain')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.ehlo()
    s.sendmail(sender, to, msg.as_string())
    s.quit()

class RecoveryEmail(Base):
    __tablename__ = 'recovery_email'
    jid = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False)
    confirmed = Column(Boolean, default=False)
    code = Column(Integer, nullable=True)
    password_code = Column(String(255), nullable=True)


if __name__ == "__main__":
    application.run()

config = configparser.RawConfigParser()
config.read('/etc/pimuxbot.cfg')
db_user = config.get('DB', 'username')
db_pass = config.get('DB', 'password')
db_host = config.get('DB', 'host')
db_name = config.get('DB', 'name')
engine = create_engine('postgresql://%s:%s@%s/%s' % (db_user, db_pass, db_host, db_name))
session = sessionmaker()
session.configure(bind=engine)
Base.metadata.create_all(engine)
s = session()

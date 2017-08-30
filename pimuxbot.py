#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pip3 install dnspython

import re
import random
import sleekxmpp
import configparser
import smtplib
from email.mime.text import MIMEText
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from collections import OrderedDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class PimuxBot(sleekxmpp.ClientXMPP):

    """
    This XMPP bot will get your commands and do the associated acitons.
    """

    def __init__(self, s, jid, password):
        self.s = s
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)


    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] == 'chat':
            pm = PimuxManager(self.s, msg['from'], msg['body'])
            reply = pm.process()
            msg.reply(reply).send()


class PimuxManager(object):

    """
    Management class for this server
    """

    commands = OrderedDict([
        ('help', 'prints this help message'),
        ('status', 'prints status'),
        ('setmail', 'sets e-mail address for password recovery'),
        ('code', 'validates e-mail address for password recovery via code')
    ])

    def __init__(self, s, jid, body):
        self.s = s
        self.jid = re.sub(r'/+.*$', '', str(jid))
        self.body = body
        if config.getboolean('System', 'debug'):
            print('message from %s received' % self.jid)
        if re.match('^.*@pimux.de$', self.jid):
            self.isPimuxUser = True
        else:
            self.isPimuxUser = False
        self.config = configparser.RawConfigParser()
        self.config.read('pimuxbot.cfg')

    def process(self):
        if self.isPimuxUser:
            command = self.__getCommand()
            if command in self.commands.keys():
                if command == 'help':
                    message = self.__help()
                elif command == 'status':
                    message = self.__getStatus()
                elif command == 'setmail':
                    email = self.__getParam()
                    if email:
                        message = self.__setMail(email)
                    else:
                        message = 'usage: setmail foobar@example.org'
                elif command == 'code':
                    code = self.__getParam()
                    if code:
                        message = self.__validateCode(code)
                    else:
                        message = 'code not found'
            else:
                message = ('Unknown command. Type "help" for a list of '
                           'commands.')
        else:
            message = ('Sorry, I don\'t talk to strangers. You need an '
                       'account at pimux.de which you can register for free.')
        return message

    def __getCommand(self):
        command = self.body.split(' ', 1)[0]
        return command

    def __getParam(self):
        try:
            param = self.body.split(' ', 1)[1]
        except IndexError:
            param = False
        return param

    def __help(self):
        helptext = 'Hello %s, I am the bot of pimux.de.\n' % self.jid
        helptext += 'available commands:\n\n'
        for key in self.commands:
            helptext += key + ': ' + self.commands[key] + '\n'
        return helptext

    def __getStatus(self):
        re = self.s.query(RecoveryEmail).filter(RecoveryEmail.jid==self.jid).one_or_none()
        if re:
            message = 'Current password recovery e-mail: %s' % re.email
            if re.confirmed:
                message += "\nYour e-mail address was successfully validated."
            else:
                message += "\nYour e-mail address was NOT validated yet and cannot be used."
        else:
            message = 'No password recovery e-mail configured.'
        return message

    def __sendMail(self, to, subject, message):
        sender = 'pimux@pimux.de'
        msg = MIMEText(message, 'plain')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        s = smtplib.SMTP('localhost')
        s.ehlo()
        s.sendmail(sender, to, msg.as_string())
        s.quit()

    def __setMail(self, email):
        code = random.randint(1000,9999)
        re = RecoveryEmail(jid=self.jid, email=email, code=code)
        self.s.merge(re)
        self.s.commit()
        msg = (
            'Please verify your e-mail address by sending '
            '"code %s" via XMPP back.'
        ) % str(code)
        self.__sendMail(email, 'verification code for pimux.de', msg)
        message =(
            'A confirmation code was sent to %s. '
            'Please now send "code XXXX" back where XXXX is your '
            'code to verify your e-mail address.'
            ) % email
        return message

    def __validateCode(self, code):
        re = self.s.query(RecoveryEmail).filter(RecoveryEmail.jid==self.jid, RecoveryEmail.code==code)
        if re:
            re = RecoveryEmail(jid=self.jid, confirmed=True, code=None)
            self.s.merge(re)
            self.s.commit()
            message = 'code valid'
        else:
            message = 'code invalid'
        return message

class RecoveryEmail(Base):
    __tablename__ = 'recovery_email'
    jid = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False)
    confirmed = Column(Boolean, default=False)
    code = Column(Integer, nullable=True)


if __name__ == '__main__':
    config = configparser.RawConfigParser()
    config.read('/etc/pimuxbot.cfg')
    jid = config.get('Account', 'jid')
    password = config.get('Account', 'password')
    db_user = config.get('DB', 'username')
    db_pass = config.get('DB', 'password')
    db_host = config.get('DB', 'host')
    db_name = config.get('DB', 'name')
    db_type = config.get('DB', 'type')

# test if the db type is even set
try: 
    db_type
# if it is not set print an error
except NameError:
    if config.getboolean('System', 'debug'):
            print('Database Type is not set.')

if db_type = 'postgres':
    engine = create_engine('postgresql://%s:%s@%s/%s' % (db_user, db_pass, db_host, db_name))

if db_type = 'mysql:'    
    engine = create_engine('mysql+mysqlconnector://%s:%s@%s/%s' % (db_user, db_pass, db_host, db_name))

    session = sessionmaker()
    session.configure(bind=engine)
    Base.metadata.create_all(engine)
    s = session()

    xmpp = PimuxBot(s, jid, password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # XMPP Ping
    #xmpp.ca_certs = config.get('System', 'capath')

    # Connect to the XMPP server and start processing XMPP stanzas.
    if config.getboolean('System', 'debug'):
        print('beginning connection as %s' % jid)
    if xmpp.connect(reattempt=True):
        if config.getboolean('System', 'debug'):
            print('connected as %s' % jid)
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

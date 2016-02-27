#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import re
import sys
import imp
import random
import string
import sleekxmpp
import ConfigParser

# This is necessary because I have installed vmm from source.
# I will find a better way in the future.
sys.path.append('/usr/local/src/vmm-0.6.2/build/lib/')
from VirtualMailManager import handler
from VirtualMailManager import account
from VirtualMailManager import errors
from collections import OrderedDict


# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input


class PimuxBot(sleekxmpp.ClientXMPP):

    """
    This XMPP bot will get your commands and do the associated acitons.
    """

    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        if msg['type'] == 'chat':
            pm = PimuxManager(msg['from'], msg['body'])
            reply = pm.process()
            msg.reply(reply).send()


class PimuxManager(object):

    """
    Management class for this server
    """

    commands = OrderedDict([
        ('help', 'prints this help message'),
        ('status', 'prints status and used services'),
        ('register email', 'register your email address'),
        ('register owncloud', 'register your ownCloud account'),
        ('resetpw email', 'reset your email password'),
        ('resetpw owncloud', 'reset your ownCloud password'),
        ('get mailconfig', 'prints mail configurations and webmail url'),
        ('moo', 'get a class of milk')
    ])

    def __init__(self, jid, body):
        self.jid = re.sub(r'/+.*$', '', str(jid))
        self.body = body
        if config.get('System', 'debug'):
            print 'message from %s received' % self.jid
        if re.match('^.*@pimux.de$', self.jid):
            self.isPimuxUser = True
        else:
            self.isPimuxUser = False
        self.config = ConfigParser.RawConfigParser()
        self.config.read('pimuxbot.cfg')

        self.handler = handler.Handler()
        import __builtin__
        if 'cfg_dget' not in __builtin__.__dict__:
            self.handler.cfg_install()

    def process(self):
        if self.isPimuxUser:
            command = self.__getCommand()
            if command in self.commands.keys():
                if command == 'help':
                    message = self.__help()
                elif command == 'status':
                    message = self.__getStatus()
                elif command == 'register email':
                    message = self.__registerEmail()
                elif command == 'register owncloud':
                    message = self.__registerOwnCloud()
                elif command == 'resetpw email':
                    message = self.__resetPwEmail()
                elif command == 'resetpw owncloud':
                    message = self.__resetPwOwnCloud()
                elif command == 'get mailconfig':
                    message = self.__getMailConfig()
                elif command == 'moo':
                    message = 'mooooo!'
            else:
                message = ('Unknown command. Type "help" for a list of '
                           'commands.')
        else:
            message = ('Sorry, I don\'t talk to strangers. You need an '
                       'account at pimux.de which you can register for free.')
        return message

    def __getCommand(self):
        command = self.body.strip().lower()
        return command

    def __help(self):
        helptext = 'Hello %s, this is pimux bot version 0.1 :-)\n' % self.jid
        helptext += 'available commands:\n\n'
        for key in self.commands:
            helptext += key + ': ' + self.commands[key] + '\n'
        return helptext

    def __getStatus(self):
        message = ('A more detailed status check will be implemented soon. '
                   'If you receive these messages, the bot should be working.')
        return message

    def __registerEmail(self):
        password = self.__genPassword()
        if not self.__emailExists():
            userInfo = self.handler.user_add(self.jid, password)
            message = ('Done! Your password for you email address %s is %s. '
                       'Please change it immediately. Visit %s for logging '
                       ' in.') % (self.jid, password)
        else:
            message = "You already have an email account! (%s)" % self.jid
        return message

    def __emailExists(self):
        try:
            userInfo = self.handler.user_info(self.jid)
            if userInfo:
                exists = True
        except errors.VMMError:
            # no such user
            exists = False
        return exists

    def __genPassword(self):
        s = string.lowercase + string.uppercase + string.digits
        s = ''.join(random.sample(s, 10))
        return s

    def __resetPwEmail(self):
        if self.__emailExists():
            password = self.__genPassword()
            self.handler.user_password(self.jid, password)
            message = 'Your email password has been reset: %s' % password
        else:
            message = 'You don\'t have a registered email Address at pimux.de'
        return message

    def __registerOwnCloud(self):
        message = 'ownCloud registration will be available soon'
        return message

    def __resetPwOwnCloud(self):
        message = 'ownCloud registration will be available soon'
        return message

    def __getMailConfig(self):
        message = 'WebMail URL: %s\n' % self.config.get('Mail', 'webmail')
        message += 'POP Server: %s\n' % self.config.get('Mail', 'pop')
        message += 'IMAP Server: %s\n' % self.config.get('Mail', 'imap')
        message += 'SMTP Server: %s\n' % self.config.get('Mail', 'smtp')
        return message


if __name__ == '__main__':
    config = ConfigParser.RawConfigParser()
    config.read('pimuxbot.cfg')
    jid = config.get('Account', 'jid')
    password = config.get('Account', 'password')
    xmpp = PimuxBot(jid, password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # XMPP Ping
    #xmpp.ca_certs = config.get('System', 'capath')

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        if config.get('System', 'debug'):
            print 'connecting as %s' % jid
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

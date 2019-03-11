import email
import imaplib
import subprocess
import time
import os
import sys
import conf
import auth
import util
import parse
from entities import Notification


class PhabAPI:
    def __init__(self, phab_handler, stmp_server, email, password, label):
        self.stmp_server = stmp_server
        self.email = email
        self.password = password
        self.label = label
        self.last_id = None
        self.connection = None
        self.diff_parser = parser.DiffParser(phab_handler)
        self.task_parser = parser.TaskParser(phab_handler)

    def start(self):
        self._connect()
        while True:
            self._check_loop()
            time.sleep(5)

    def _connect(self):
        self.connection = imaplib.IMAP4_SSL(self.stmp_server)
        self.connection.login(self.email, self.password)
        self.connection.select(self.label)

        if self.last_id is None:
            ids = self._get_new_email_ids(-1)
            self.last_id = ids[-1] if len(ids) > 0 else 0

    def _get_new_email_ids(self):
        _, data = self.connection.search(None, 'ALL')
        str_ids = data[0].split()
        new_ids = [int(id) for id in str_ids if int(id) > int(self.last_id)]

        if len(new_ids) > 0:
            self.last_id = new_ids[-1]

        return new_ids

    def _get_new_email(self):
        new_ids = self._get_new_email_ids()

        if len(new_ids) == 0:
            return []

        ids = ",".join([str(id) for id in new_ids])
        typ, data = self.connection.fetch(ids, '(RFC822)' )
        new_mail = []

        for response_part in data:
            if isinstance(response_part, tuple):
                mail = email.message_from_string(response_part[1].decode())
                new_mail.append(mail)

        return new_mail

    def _check_loop(self):
        new_mail = self._get_new_email()
        notifications = []

        for mail in new_mail:
            phab_id = util.regex_phab_id(mail['subject'])
            phab_desc = util.get_regex_match(mail['subject'], "[DT][0-9]+: (.*)")

            body = mail.get_payload(decode=True)
            if mail.is_multipart():
                body = ''.join([str(p) for p in body.get_payload(decode=True)])

            parser = self.task_parser if phab_id[0] == 'T' else self.diff_parser
            parsed = parser.parse(phab_id, phab_desc, body.decode())
            notifications = notifications + parsed

        return notifications


class PhabHandler():
    def on_diff_new(self, id, desc, act_user):
        raise NotImplementedError("on_diff_new is not implemented")

    def on_diff_request_changes(self, id, desc, act_user):
        raise NotImplementedError("on_diff_request_changes is not implemented")

    def on_diff_comment(self, id, desc, act_user, comment):
        raise NotImplementedError("on_diff_comment is not implemented")

    def on_diff_inline_comments(self, id, desc, act_user, comments):
        raise NotImplementedError("on_diff_inline_comments is not implemented")

    def on_diff_ready_to_land(self, id, desc):
        raise NotImplementedError("on_diff_ready_to_land is not implemented")

    def on_task_comment(self, id, desc, act_user, comment):
        raise NotImplementedError("on_task_comment is not implemented")

    def on_task_move(self, id, desc, act_user):
        raise NotImplementedError("on_task_move is not implemented")
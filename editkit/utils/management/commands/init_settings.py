import os
from random import choice


class Command(object):
    """
    Asks questions to auto-populate the local settings.
    """

    def _write_settings(self, vals):
        localsettings = open(os.path.join(self.DATA_ROOT, 'conf',
            'localsettings.py')).read()
        for k, v in vals.iteritems():
            localsettings = localsettings.replace(k, v)

        f = open(os.path.join(self.DATA_ROOT, 'conf',
            'localsettings.py'), 'w')
        f.write(localsettings)
        f.close()

    def _generate_secret_key(self):
        """
        Generate a local secret key.
        """
        secret_key = ''.join([
            choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
            for i in range(50)
        ])
        return secret_key

    def handle(self, *args, **options):
        self._write_settings({
            'SECRETKEYHERE': self._generate_secret_key(),
            'DBNAMEHERE': os.path.join(self.DATA_ROOT, 'data',
                                       'editkit.sqlite3'),
            'WHOOSHPATHHERE': os.path.join(self.DATA_ROOT, 'data',
                                       'search_index'),
        })


def run(DATA_ROOT=None, PROJECT_ROOT=None):
    c = Command()
    c.DATA_ROOT = DATA_ROOT
    c.PROJECT_ROOT = PROJECT_ROOT
    c.handle()

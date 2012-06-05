import os
import subprocess
import string
from random import choice
import tempfile


class Command(object):
    """
    Creates a DB user, DB name, and strong, random DB password.
    """

    def gen_password(self):
        chars = string.letters + string.digits
        length = 30
        return ''.join(choice(chars) for _ in range(length))

    def create_db(self):
        default_username = 'editkit'
        default_dbname = 'editkit'

        rand_password = self.gen_password()
        # First, let's try and create the default username.
        username = default_username
        p = subprocess.Popen("""sudo -u postgres psql -d template1 """
            """-c "CREATE USER %s WITH PASSWORD '%s'" """
            % (username, rand_password),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        retval = p.wait()
        if retval != 0:
            for line in p.stdout:
                print line.strip()
            # Oops, default name already taken.  This is probably their
            # second install on the same system.  Let's prompt for a new
            # username.
            print ("Default DB username '%s' already taken. "
                   "Enter new DB username:" % default_username)
            username = raw_input().strip()
            p = subprocess.Popen("""sudo -u postgres psql -d template1 """
                """-c "CREATE USER %s WITH PASSWORD '%s'" """
                % (username, rand_password),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            retval = p.wait()
            for line in p.stdout:
                if line.strip():
                    print line.strip()

        # Now let's try and create the default database.'
        dbname = default_dbname
        p = subprocess.Popen("""sudo -u postgres createdb -E UTF8 """
                """-T template_postgis -O %s %s""" % (username, dbname),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        retval = p.wait()
        if retval != 0:
            for line in p.stdout:
                print line.strip()
            # Oops, db already exists.  This is probably their second
            # install on the same system.  Let's prompt for a new
            # database name.
            print ("Default DB name '%s' already taken. "
                   "Enter new DB name:" % default_dbname)
            dbname = raw_input().strip()
            p = subprocess.Popen("""sudo -u postgres createdb -E UTF8 """
                """-T template_postgis -O %s %s""" % (username, dbname),
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            retval = p.wait()
            for line in p.stdout:
                if line.strip():
                    print line.strip()
            if retval != 0:
                print "Error creating database"
                return

        self.dbname = dbname
        self.username = username
        self.password = rand_password
        print "Database '%s' with username '%s' created!" % (dbname, username)

    def update_settings(self):
        localsettings = open(os.path.join(self.DATA_ROOT, 'conf',
            'localsettings.py')).read()
        localsettings = localsettings.replace('DBENGINEHERE', self.dbengine)
        localsettings = localsettings.replace('DBNAMEHERE', self.dbname)
        if self.POSTGRES:
            localsettings = localsettings.replace('DBUSERNAMEHERE', self.username)
            localsettings = localsettings.replace('DBPASSWORDHERE', self.password)
        f = open(os.path.join(self.DATA_ROOT, 'conf',
            'localsettings.py'), 'w')
        f.write(localsettings)
        f.close()

    def handle(self, *args, **options):
        if self.POSTGRES:
            self.dbengine = 'django.db.backends.postgresql_psycopg2'
            self.create_db()
        else:
            self.dbengine = 'django.db.backends.sqlite3'
            self.dbname = os.path.join(self.DATA_ROOT, 'data',
                                       'editkit.sqlite3');
        self.update_settings()


def run(DATA_ROOT=None, PROJECT_ROOT=None, POSTGRES=None):
    c = Command()
    c.DATA_ROOT = DATA_ROOT
    c.PROJECT_ROOT = PROJECT_ROOT
    c.POSTGRES = POSTGRES
    c.handle()

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = ('Imports pages from an existing MediaWiki site.  '
            'Clears out any existing data.')

    def handle(self, *args, **options):
        from importers import mediawiki
        mediawiki.run()

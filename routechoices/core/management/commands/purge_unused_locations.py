from django.core.management.base import BaseCommand

from datetime import timedelta
from django.utils.timezone import now

from routechoices.core.models import Device


class Command(BaseCommand):
    help = 'Delete unused locations after 14 days'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', default=False)

    def handle(self, *args, **options):
        force = options['force']
        deleted_count = 0
        devices = Device.objects.all()
        for device in devices:
            locs = device.locations
            device.remove_duplicates(force)
            periods_used = []
            two_weeks_ago = now() - timedelta(days=14)
            competitors = device.competitor_set.all()
            for competitor in competitors:
                event = competitor.event
                start = event.start_date
                if competitor.start_time:
                    start = competitor.start_time
                end = None
                if event.end_date:
                    end = min(event.end_date, two_weeks_ago)
                else:
                    end = two_weeks_ago
                periods_used.append((start, end))
            valid_indexes = []
            for idx, timestamp in enumerate(locs['timestamps']):
                is_valid = False
                if timestamp >= two_weeks_ago.timestamp():
                    is_valid = True
                for p in periods_used:
                    if p[0].timestamp() <= timestamp <= p[1].timestamp() \
                            or timestamp >= two_weeks_ago.timestamp():
                        is_valid = True
                        break
                if is_valid:
                    valid_indexes.append(idx)
            dev_del_loc_count = len(locs['timestamps']) - len(valid_indexes)
            if dev_del_loc_count:
                self.stdout.write(
                    'Device %s, extra %d locations' % (
                        device.aid,
                        dev_del_loc_count
                    )
                )
            deleted_count += dev_del_loc_count
            if force and dev_del_loc_count:
                new_locs = {
                    'timestamps':
                        [locs['timestamps'][i] for i in valid_indexes],
                    'latitudes':
                        [locs['latitudes'][i] for i in valid_indexes],
                    'longitudes':
                        [locs['longitudes'][i] for i in valid_indexes],
                }
                device.locations = new_locs
                device.save()
        if force:
            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully removed %d Locations' % deleted_count
                )
            )
        else:
            self.stdout.write('Would remove %d Locations' % deleted_count)

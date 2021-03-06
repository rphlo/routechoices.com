import requests
import arrow
from PIL import Image
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

from background_task import background

from routechoices.core.models import Map, Event, Device, Competitor, Club
from routechoices.lib.helper import short_random_key, \
    three_point_calibration_to_corners

GPSSEURANTA_EVENT_URL = 'http://www.tulospalvelu.fi/gps/'
LOGGATOR_EVENT_URL = 'https://loggator.com/api/events/'


class EventImportError(Exception):
    pass


class MapImportError(Exception):
    pass


def get_gpsseuranta_club():
    admins = User.objects.filter(is_superuser=True)
    club, created = Club.objects.get_or_create(
        slug='gpsseuranta',
        defaults={
            'name': 'GPS Seuranta'
        }
    )
    if created:
        club.admins.set(admins)
        club.save()
    return club


def get_loggator_club():
    admins = User.objects.filter(is_superuser=True)
    club, created = Club.objects.get_or_create(
        slug='loggator',
        defaults={
            'name': 'Loggator'
        }
    )
    if created:
        club.admins.set(admins)
        club.save()
    return club


def import_map_from_gps_seuranta(club, map_data, name, event_id):
    map_url = GPSSEURANTA_EVENT_URL + event_id + '/map'
    r = requests.get(map_url)
    map_model, created = Map.objects.get_or_create(
        name=name,
        club=club,
    )
    if not created:
        return map_model
    if r.status_code != 200:
        raise MapImportError('API returned error code')
    map_file = ContentFile(r.content)
    with Image.open(map_file) as img:
        width, height = img.size
    corners = three_point_calibration_to_corners(
        map_data,
        width,
        height
    )
    coordinates = ','.join([
        str(x) for x in corners
    ])
    map_model.image.save('imported_image', map_file, save=False)
    map_model.corners_coordinates = coordinates
    map_model.save()
    return map_model


def decode_track_line(device, data, min_date=None, max_date=None):
    if not data:
        return min_date, max_date
    o_pt = data[0].split('_')
    if o_pt[0] == '*' or o_pt[1] == '*' or o_pt[2] == '*':
        return min_date, max_date
    t = arrow.get(int(o_pt[0]) + 1136073600).datetime
    prev_loc = {
        'lat': int(o_pt[2]) * 1.0 / 1e5,
        'lon': int(o_pt[1]) * 2.0 / 1e5,
        'datetime': t,
    }
    device.add_location(
        prev_loc['lat'],
        prev_loc['lon'],
        t.timestamp(),
        False
    )
    if min_date is None or t < min_date:
        min_date = t
    if max_date is None or t > max_date:
        max_date = t
    loc_array = []
    for p in data[1:]:
        if len(p) < 3:
            continue
        if '_' in p:
            pt = p.split('_')
            if pt[0] == '*':
                pt[0] = 0
            if pt[1] == '*':
                pt[1] = 0
            if pt[2] == '*':
                pt[2] = 0
            dt = int(pt[0])
            dlng = int(pt[1])
            dlat = int(pt[2])
        else:
            chars = \
                '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
                'abcdefghijklmnopqrstuvwxyz'
            dt = chars.index(p[0]) - 31
            dlng = chars.index(p[1]) - 31
            dlat = chars.index(p[2]) - 31
        t = arrow.get(prev_loc['datetime'].timestamp() + dt).datetime

        prev_loc = {
            'lat': ((prev_loc['lat'] * 100000) + dlat) / 100000,
            'lon': ((prev_loc['lon'] * 50000) + dlng) / 50000,
            'datetime': t,
        }
        loc_array.append({
            'timestamp': t.timestamp(),
            'latitude': prev_loc['lat'],
            'longitude': prev_loc['lon'],
        })
        if t < min_date:
            min_date = t
        if t > max_date:
            max_date = t
    device.add_locations(loc_array, False)
    return min_date, max_date


@background(schedule=0)
def import_single_event_from_gps_seuranta(event_id):
    club = get_gpsseuranta_club()
    event_url = GPSSEURANTA_EVENT_URL + event_id + '/init.txt'
    r = requests.get(event_url)
    if r.status_code != 200:
        raise EventImportError('API returned error code')
    event_raw_data = r.text
    event_data = {'COMPETITOR': []}
    for line in event_raw_data.split('\n'):
        try:
            key, val = line.strip().split(':')
            if key != 'COMPETITOR':
                event_data[key] = val
            else:
                event_data[key].append(val)
        except ValueError:
            continue

    event_start_date = None
    event_end_date = None
    device_map = {}
    event_tracks_url = GPSSEURANTA_EVENT_URL + event_id + '/data.lst'
    r = requests.get(event_tracks_url)
    if r.status_code == 200:
        tracks_raw = r.text
        for line in tracks_raw.split('\n'):
            d = line.strip().split('.')
            if len(d) == 0:
                continue
            dev_id = d[0]
            if '_' in dev_id:
                dev_id, _ = dev_id.split('_', 1)
            if not device_map.get(dev_id):
                device_map[dev_id] = Device.objects.create(
                    aid=short_random_key() + '_SEU',
                    is_gpx=True,
                )
            dev = device_map[dev_id]
            event_start_date, event_end_date = decode_track_line(
                dev,
                d[1:],
                event_start_date,
                event_end_date,
            )

    event, created = Event.objects.get_or_create(
        club=club,
        slug=event_id,
        defaults={
            'name': event_data['RACENAME'],
            'start_date': event_start_date,
            'end_date': event_end_date,
        }
    )
    if not created:
        for dev in device_map:
            device_map[dev].delete()
        return

    event_map_data = event_data.get('CALIBRATION')
    event_map = None
    try:
        event_map = import_map_from_gps_seuranta(
            club,
            event_map_data,
            event_data['RACENAME'],
            event_id
        )
    except MapImportError:
        pass

    if event_map:
        event.map = event_map
        event.save()

    for c_raw in event_data['COMPETITOR']:
        c_data = c_raw.strip().split('|')
        start_time_raw = c_data[1] + c_data[2]
        if len(start_time_raw) == 12:
            start_time = arrow.get(
                c_data[1] + c_data[2],
                'YYYYMMDDHHmm'
            )
        else:
            start_time = arrow.get(
                c_data[1] + c_data[2],
                'YYYYMMDDHHmmss'
            )
        start_time = start_time.shift(
            minutes=-int(event_data.get('TIMEZONE', 0))
        ).datetime
        Competitor.objects.create(
            name=c_data[3],
            short_name=c_data[4],
            start_time=start_time,
            device=device_map.get(c_data[0]),
            event=event,
        )
        dev = device_map.get(c_data[0])
        if dev:
            dev.save()
    return event


def import_map_from_loggator(club, map_data, name):
    map_url = map_data['url']
    r = requests.get(map_url)
    map_model, created = Map.objects.get_or_create(
        name=name,
        club=club,
    )
    if not created:
        return map_model
    if r.status_code != 200:
        raise MapImportError('API returned error code')
    map_file = ContentFile(r.content)
    coordinates = ','.join([
        str(map_data['coordinates']['topLeft']['lat']),
        str(map_data['coordinates']['topLeft']['lng']),
        str(map_data['coordinates']['topRight']['lat']),
        str(map_data['coordinates']['topRight']['lng']),
        str(map_data['coordinates']['bottomRight']['lat']),
        str(map_data['coordinates']['bottomRight']['lng']),
        str(map_data['coordinates']['bottomLeft']['lat']),
        str(map_data['coordinates']['bottomLeft']['lng'])
    ])
    map_model.image.save('imported_image', map_file, save=False)
    map_model.corners_coordinates = coordinates
    map_model.save()
    return map_model


@background(schedule=0)
def import_single_event_from_loggator(event_id):
    club = get_loggator_club()
    event_url = LOGGATOR_EVENT_URL + event_id + '.json'
    r = requests.get(event_url)
    if r.status_code != 200:
        raise EventImportError('API returned error code')
    event_data = r.json()
    event_map = None
    event_map_data = event_data.get('map')
    event, created = Event.objects.get_or_create(
        club=club,
        slug=event_data['event']['slug'],
        defaults={
            'name': event_data['event']['name'],
            'start_date':
                arrow.get(event_data['event']['start_date']).datetime,
            'end_date':
                arrow.get(event_data['event']['end_date']).datetime,
        }
    )
    if not created:
        return
    if event_map_data:
        try:
            event_map = import_map_from_loggator(
                club,
                event_map_data,
                event_data['event']['name']
            )
        except MapImportError:
            pass
        if event_map:
            event.map = event_map
            event.save()

    device_map = {}
    loc_array_map = {}
    r = requests.get(event_data['tracks'])
    if r.status_code == 200:
        tracks_raw = r.json()['data']
        tracks_pts = tracks_raw.split(';')
        for pt in tracks_pts:
            d = pt.split(',')
            if not device_map.get(int(d[0])):
                device_map[int(d[0])] = Device.objects.create(
                    aid=short_random_key() + '_LOG',
                    is_gpx=True,
                )
                loc_array_map[int(d[0])] = []
            loc_array_map[int(d[0])].append({
                'timestamp': arrow.get(int(d[4])).timestamp(),
                'latitude': float(d[1]),
                'longitude': float(d[2]),
            })

    for c_data in event_data['competitors']:
        Competitor.objects.create(
            name=c_data['name'],
            short_name=c_data['shortname'],
            start_time=arrow.get(c_data['start_time']).datetime,
            device=device_map.get(c_data['device_id']),
            event=event,
        )
        dev = device_map.get(c_data['device_id'])
        if dev:
            dev.add_locations(loc_array_map.get(c_data['device_id']))
    return event

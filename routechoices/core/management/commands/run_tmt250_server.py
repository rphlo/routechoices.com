# coding=utf-8
from struct import unpack, pack
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from tornado.tcpserver import TCPServer
from tornado.iostream import StreamClosedError
from tornado import gen
from tornado.ioloop import IOLoop

from routechoices.core.models import Device 


def _get_device(imei):
    try:
        return Device.objects.get(physical_device__imei=imei)
    except Device.DoesNotExist:
        return None


class TMT250Decoder():
    def __init__(self):
        self.packet = {}

    def generate_response(self, success=True):
        return pack('>i', self.packet['num_data'] if success else 0)

    def decode_alv(self, data):
        self.packet['zeroes'] = unpack('>i', data[:4])[0]
        assert(self.packet['zeroes'] == 0)
        self.packet['length'] = unpack('>i', data[4:8])[0]
        self.packet['codec'] = data[8]
        assert(self.packet['codec'] == 8)
        self.packet['num_data'] = data[9]
        self.extract_records(data)
        return self.packet

    def extract_records(self, buffer):
        remaining_data = self.packet['num_data']
        self.packet['records'] = []
        pointer = 10
        while remaining_data > 0:
            timestamp = unpack('>Q', buffer[pointer:pointer+8])[0] / 1e3
            lon = unpack('>i', buffer[pointer+9:pointer+13])[0] / 1e7
            lat = unpack('>i', buffer[pointer+13:pointer+17])[0] / 1e7

            n1 = buffer[pointer + 26]
            pointer += 27 + n1 * 2

            n2 = buffer[pointer]
            pointer += 1 +3 * n2
            
            n4 = buffer[pointer]
            pointer += 1 + 5 * n4
            
            n8 = buffer[pointer]
            pointer += 1 + 9 * n8
            self.packet['records'].append({
                'timestamp': timestamp,
                'latlon': [lat, lon],
            })
            remaining_data -= 1
        return pointer


class TMT250Connection():
    def __init__(self, stream, address):
        print('received a new connection from %s', address)
        self.imei = None
        self.waiting_for_content = False
        self.address = address
        self.stream = stream
        self.stream.set_close_callback(self._on_close)
        self.decoder = TMT250Decoder()
        self.packet_len = 0
        self.buffer = None
        self.db_device = None

    async def start_listening(self):
        print('start listening from %s', self.address)
        data = bytearray(b'0'*1234)
        try:
            data_len = await self.stream.read_into(data, partial=True)
            if(data_len < 3):
                print('too little data %s', self.address)
                await self.stream.write(pack('>H', 0))
                self.stream.close()
                return
            data = data[:data_len]
        except StreamClosedError:
            return
        imei_len = (data[0] << 8) + data[1]
        imei = data[2:].decode('ascii')
        if imei_len != len(imei):
            print('invalid identification %s, %s, %d' % (self.address, imei, imei_len))
            await self.stream.write(pack('>H', 0))
            self.stream.close()
            return
        self.db_device = await sync_to_async(_get_device, thread_sensitive=True)(imei)
        if not self.db_device:
            print('imei not registered %s, %s' % (self.address, imei))
            await self.stream.write(pack('>H', 0))
            self.stream.close()
            return
        self.imei = imei
        await self.stream.write(pack('>H', 1))
        print('%s is connected' % (self.imei))
        while await self._on_write_complete():
            pass

    async def _on_read_line(self, data):
        if not self.waiting_for_content:
            zeroes = unpack('>i', data[:4])[0]
            assert(zeroes == 0)
            self.packet_length = unpack('>i', data[4:8])[0] + 4
            if len(data) - 8 >= self.packet_length:
                await self._on_full_data(data)
            else:
                self.waiting_for_content = True
                self.buffer = bytes(data)
        elif self.packet_length > len(self.buffer):
             self.buffer += bytes(data)
        if self.packet_length <= len(self.buffer):
            await self._on_full_data(self.buffer)
    
    async def _on_write_complete(self):
        if not self.stream.reading():
            data = bytearray(b'0'*1234)
            try:
                data_len = await self.stream.read_into(data, partial=True)
                await self._on_read_line(data[:data_len])
            except StreamClosedError:
                return False
            return True

    def _on_close(self):
        print('client quit %s', self.address)

    async def _on_full_data(self, data):
        try:
            decoded = self.decoder.decode_alv(self.buffer)
        except Exception:
            print('error decoding packet')
            await self.stream.write(self.decoder.generate_response(False))
        else:
            for r in decoded.get('records', []):
                self.db_device.add_location(r['latlon'][0], r['latlon'][1], r['timestamp'], save=False)
            await sync_to_async(self.db_device.save, thread_sensitive=True)()
            self.waiting_for_content = True
        
            await self.stream.write(self.decoder.generate_response())


class TMT250Server(TCPServer):
    async def handle_stream(self, stream, address):
        c = TMT250Connection(stream, address)
        await c.start_listening()


class Command(BaseCommand):
    help = 'Run a tmt250 server.'

    def handle(self, *args, **options):
        server = TMT250Server()
        server.listen(settings.TMT250_PORT)
        IOLoop.current().start()
import os
import time

import yaml
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory, connectionDone


class UpProxyLogger:
    @staticmethod
    def log(message, timestamp=True):
        if not os.path.isdir('log'):
            os.mkdir(path='log')

        if timestamp:
            log_entry = "[%s]\t-\t%s" % (time.strftime("%Y-%m-%d %H:%M:%S"), message)
        else:
            log_entry = message

        print(log_entry)
        with open('log/%s_proxy.log' % time.strftime('%Y_%m_%d'), 'a') as f:
            f.write(log_entry + '\n')

    @staticmethod
    def log_empty():
        UpProxyLogger.log("", False)

    @staticmethod
    def log_spacer():
        UpProxyLogger.log("=" * 100, False)


class UpProxy:
    DEFAULT_GROUND = 3003
    DEFAULT_AIRBORNE = 3004

    def __init__(self):
        UpProxyLogger.log_empty()
        UpProxyLogger.log_spacer()
        UpProxyLogger.log('Up Proxy Starting')

        self.__airborne_port, self.__ground_port = self.__read_config()
        UpProxyLogger.log('Ground Port: %s, Airborne Port: %s' % (self.__airborne_port, self.__ground_port))

        self.__ground_connected = False
        self.__ground_protocol = UpProxyProtocol(self, UpProxyProtocol.GROUND)
        ground_endpoint = TCP4ServerEndpoint(reactor, self.__ground_port)
        ground_endpoint.listen(UpProxyProtocolFactory(self.__ground_protocol))

        self.__airborne_connected = False
        self.__airborne_protocol = UpProxyProtocol(self, UpProxyProtocol.AIRBORNE)
        airborne_endpoint = TCP4ServerEndpoint(reactor, self.__airborne_port)
        airborne_endpoint.listen(UpProxyProtocolFactory(self.__airborne_protocol))

    def run(self):
        reactor.run()

    def on_data_received(self, data, mode):
        if mode == UpProxyProtocol.AIRBORNE and self.__ground_connected and self.__ground_protocol.transport is not None:
            self.__ground_protocol.transport.write(data)
        elif mode == UpProxyProtocol.GROUND and self.__airborne_protocol and self.__airborne_protocol.transport is not None:
            self.__airborne_protocol.transport.write(data)

    def on_connection_made(self, mode):
        if mode == UpProxyProtocol.AIRBORNE:
            self.__airborne_connected = True
        elif mode == UpProxyProtocol.GROUND:
            self.__ground_connected = True

    def on_connection_lost(self, mode):
        if mode == UpProxyProtocol.AIRBORNE:
            self.__airborne_connected = False
        elif mode == UpProxyProtocol.GROUND:
            self.__ground_connected = False

    @staticmethod
    def __read_config():
        with open('config/proxy.yml') as f:
            config = yaml.load(f)
            return config.get('airborne port', UpProxy.DEFAULT_AIRBORNE), config.get('ground port',
                                                                                     UpProxy.DEFAULT_GROUND)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        UpProxyLogger.log("Up Proxy exiting")
        UpProxyLogger.log_spacer()


class UpProxyProtocol(Protocol):
    AIRBORNE = 'AIRBORNE'
    GROUND = 'GROUND'

    def __init__(self, callbacks, mode):
        self.__callbacks = callbacks
        self.__mode = mode

    def dataReceived(self, data):
        super().dataReceived(data)
        self.callbacks.on_data_received(data, self.mode)

    def connectionMade(self):
        super().connectionMade()
        UpProxyLogger.log("Connection from %s opened in mode %s" % (self.transport.client[0], self.mode))
        self.callbacks.on_connection_made(self.mode)

    def connectionLost(self, reason=connectionDone):
        super().connectionLost(reason)
        UpProxyLogger.log("Connection from %s in mode %s closed" % (self.transport.client[0], self.mode))
        self.callbacks.on_connection_lost(self.mode)

    @property
    def callbacks(self):
        return self.__callbacks

    @property
    def mode(self):
        return self.__mode


class UpProxyProtocolFactory(Factory):
    def __init__(self, protocol):
        super().__init__()
        self.__protocol = protocol

    def buildProtocol(self, addr):
        return self.__protocol


if __name__ == '__main__':
    proxy = UpProxy()
    with proxy:
        proxy.run()

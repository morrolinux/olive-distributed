# sample from: https://stackoverflow.com/questions/34499331/pyro4-failed-to-locate-the-nameserver
import Pyro4

@Pyro4.expose
class GreetingMaker(object):
    def get_fortune(self, name):
        return "Hello, {0}. Here is your fortune message:\n" \
               "Behold the warranty -- the bold print giveth and the fine print taketh away.".format(name)


Pyro4.Daemon.serveSimple({
    GreetingMaker: 'Greeting',
}, host="0.0.0.0", port=9090, ns=False, verbose=True)
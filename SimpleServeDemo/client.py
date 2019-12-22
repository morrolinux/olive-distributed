# sample from: https://stackoverflow.com/questions/34499331/pyro4-failed-to-locate-the-nameserver
import Pyro4

ipAddressServer = ""  # TODO add your server remote IP here

# Works for Python3, see edit above for notes on Python 2.x
name = input("What is your name? ").strip()

greetingMaker = Pyro4.core.Proxy('PYRO:Greeting@' + ipAddressServer + ':9090')
print(greetingMaker.get_fortune(name))   # call method normally
import pika
from datetime import datetime
from multiprocessing import Process, Array
import re
import os
import sys


class MetaClass(type):
    _instance = {}

    def __call__(cls, *args, **kwargs):
        """ Singleton Design Pattern """

        if cls not in cls._instance:
            cls._instance[cls] = super(MetaClass, cls).__call__(*args, **kwargs)
            return cls._instance[cls]


class RabbitMQConfigure(metaclass=MetaClass):
    def __init__(self, host='localhost', exchange='topic_chat', exchange_type='topic'):
        self.host = host
        self.exchange = exchange
        self.exchange_type = exchange_type


class RabitMQ():
    def __init__(self, server):
        self.server = server
        self._connection = pika.BlockingConnection(pika.ConnectionParameters(host=self.server.host, heartbeat=None))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=self.server.exchange, exchange_type=self.server.exchange_type)
        self.result = self._channel.queue_declare('', exclusive=True)
        self.queue_name = self.result.method.queue
        self.binding_keys = []
        self.users = []

    def publish(self, rkey, payload={}):
        self._channel.basic_publish(exchange=self.server.exchange,
                                    routing_key=rkey,
                                    body=str(payload))

    def callback(self, ch, method, properties, body):
        body_dec = body.decode().split(',')
        user_body = body_dec[0].translate(str.maketrans('', '', '!@#$'))
        message_body = body_dec[1].translate(str.maketrans('', '', '!@#$'))

        user_body = re.sub('\'|\"|\(|\)', '', body_dec[0])
        message_body = re.sub('\'|\"|\(|\)', '', body_dec[1])

        if self.users.count(user_body) == 0:
            self.users.append(user_body)

        if user_body != user:
            print("", end="\r")
            if method.routing_key == user:
                print("<PM> [{}]:{}".format(user_body, message_body))
            else:
                print("<{}> [{}]:{}".format(method.routing_key, user_body, message_body))
            # print("", end="\r")
            print("<{}> [{}]:".format(binding_key.value.decode(), user), end=" ")
            sys.stdout.flush()

    def consume(self):
        self._channel.basic_consume(queue=self.queue_name,
                                    on_message_callback=self.callback,
                                    auto_ack=True)
        self._channel.start_consuming()

    def list_queues(self):
        print("Lista dostepnych kanałów:", end=" ")
        for bkey in self.binding_keys:
            if bkey != user:
                print("{}".format(bkey), end=" ")
        print("")
        sys.stdout.flush()

    def list_users(self):
        print("Lista podłączonych użytkowników: {}".format(self.users_arr.value), end=" ")
        print("")
        sys.stdout.flush()

    def bind_to_queue(self, b_keys):
        self.binding_keys = b_keys
        for bkey in self.binding_keys:
            self._channel.queue_bind(exchange=self.server.exchange, queue=self.queue_name, routing_key=bkey)

    def unbind_from_queue(self, bkey):
        self.binding_keys.remove(bkey)
        self._channel.queue_unbind(exchange=self.server.exchange, queue=self.queue_name, routing_key=bkey)

    def close_connection(self):
        self._channel.stop_consuming()
        self._channel.close()

    def test(self):
        print("{}".format(self._channel.consumer_tags))


if __name__ == "__main__":
    mq_server = RabbitMQConfigure(host='localhost', exchange='topic_chat', exchange_type='topic')
    rabbitmq = RabitMQ(mq_server)

    cls = lambda: os.system('cls' if os.name == 'nt' else 'clear')
    cls()

    while True:
        print("Podaj nazwe użytkownika:", end=" ")
        user = input()
        if user != '':
            break

    binding_key = Array('c', b'GLOBAL')
    binding_keys = [user, binding_key.value.decode()]

    print("******************** MENU **************************")
    print("Lista dostępnych opcji:")
    print("!join nazwa_kanału - dołaczenie do nowego kanału")
    print("!leave nazwa_kanału - opuszczenie kanału")
    print("!switch nazwa_kanału - zmiana kanału na którym chcesz pisać")
    print("!list - lista dostępnych kanałów")
    print("@user_name - wyślij prywatną wiadomość")
    print("****************************************************")

    print("Dołączanie do kanalu {}".format(binding_key.value.decode()))
    message = "Użytkownik: {} dołączył do kanału {} : {}".format(user, binding_key.value.decode(), str(datetime.now()))
    rabbitmq.bind_to_queue(binding_keys)
    rabbitmq.publish(binding_key.value.decode(), payload=(user, message))
    p = Process(target=rabbitmq.consume)
    p.start()
    rabbitmq.list_queues()

    while True:
        while True:
            print("<{}> [{}]:".format(binding_key.value.decode(), user), end=" ")
            message = input()
            if message != '':
                break
        if message[0:5] == '!join':
            message_split = message.split(' ')
            join_queue = message_split[1]
            binding_keys.append(join_queue)
            binding_keys = list(set(binding_keys))
            rabbitmq.bind_to_queue(binding_keys)
            binding_key.value = join_queue.encode()
            message = "Użytkownik: {} dołączył do kanału {} : {}".format(user, binding_key.value.decode(),
                                                                         str(datetime.now()))
            rabbitmq.publish(binding_key.value.decode(), payload=(user, message))
        elif message[0:6] == '!leave':
            message_split = message.split(' ')
            leave_queue = message_split[1]
            for b_key in binding_keys:
                if b_key == leave_queue:
                    rabbitmq.unbind_from_queue(leave_queue)
                    message = "Użytkownik: {} opuścił kanał {} : {}".format(user, binding_key.value.decode(),
                                                                                 str(datetime.now()))
                    rabbitmq.publish(binding_key.value.decode(), payload=(user, message))
                    break
            rabbitmq.list_queues()
            print("Proszę podać nazwę kanału z na ktorym chcesz pisac:", end=" ")
            bkey_in = input()
            for b_key in binding_keys:
                if b_key == bkey_in:
                    binding_key.value = b_key.encode()
                    break
            if binding_key.value.decode() != bkey_in:
                print("Nie masz dostępu do kanału: {}, ustawiony zostanie kanał GLOBAL".format(bkey_in))
                binding_key.value = "GLOBAL".encode()
        elif message[0:7] == '!switch':
            message_split = message.split(' ')
            switch_queue = message_split[1]
            for b_key in binding_keys:
                if b_key == switch_queue:
                    binding_key.value = b_key.encode()
                    break
            if binding_key.value.decode() != switch_queue:
                print("Nie masz dostępu do kanału: {}".format(switch_queue))
        elif message[0:5] == '!list':
            rabbitmq.list_queues()
        elif message[0:6] == '!users':
            rabbitmq.list_users()
        elif message[0:1] == '@':
            message_split = message.split(' ')
            pm_bkey = message_split[0]
            pm_message = message_split[1:]
            rabbitmq.publish(pm_bkey[1:], payload=(user, str(" ".join(pm_message))))
        elif message[0:2] == '!q':
            break
        else:
            rabbitmq.publish(binding_key.value.decode(), payload=(user, message))

    p.terminate()
    rabbitmq.close_connection()

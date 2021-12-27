import threading
import time 
from queue import Queue

print_lock = threading.Lock()

class MyThread(threading.Thread):
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.receive_messages = args[0]

    def run(self):
        print(threading.currentThread().getName(), self.receive_messages)
        val = self.queue.get()
        self.do_thing_with_message(val)

    def do_thing_with_message(self, message):
        if self.receive_messages:
            with print_lock:
                print(f'{threading.currentThread().getName()} received: {message}')
        else:
            print(f'{threading.currentThread().getName()} says: "I hate life."')
            time.sleep(4)

if __name__ == '__main__':
    threads = []
    for t in range(10):
        q = Queue()
        threads.append(MyThread(q, args=(t % 2 == 0,)))
        threads[t].start()
        time.sleep(0.1)

    time.sleep(2)

    for t in threads:
        t.queue.put("Print this!")

    print('waiting?')

    for t in threads:
        t.join()
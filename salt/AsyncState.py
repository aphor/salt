from salt.utils.process import MultiprocessingProcess
from salt.State import State as SyncState
from dag import DAG

def __coroutine__(func):
    '''
    decorator to initialize coroutines

    If the coroutine is created/called with
        parallel=True
    then the coroutine will run inside a
        salt.utils.process.MultiprocessingProcess
    '''
    def start(*args,**kwargs):
        parallel = False
        if 'parallel' in kwargs:
            parallel = kwargs['parallel']

        if parallel:
            cr = MultiprocessingProcess(
                target=func,
                args=*args,
                kwargs=**kwargs)
        else:
            cr = func(*args,**kwargs)
        cr.next()
        return cr

    return start


class AsyncChunk(dict):
    '''
    works like a dict, and also like a coroutine
    '''
    load = 0
    done = False
    running = False
    status = 'waiting'
    ret = None
    progress = {'load': self.load,
        'done': self.done
        'running': self.running,
        'status': self.status,
        'ret': self.ret}

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    @__coroutine__
    def __call__(self, *args, **kwargs):
        '''
        return a coroutine, using send() method to send/recieve dict() packets
        of messages

        send() accepts:
          - {'poll': None}             # This is a polling packet
          - {'state_id': 'unchanged'}  # This is a status packet
                                       # state_id reporting unchanged status

        POLL provides no status, but will return progress

        A status message will be evaluated against self.requisites() to satisfy
        requisites if matched. If either a status or poll message is recieved
        and no requisites are unsatisfied, the chunk will run.

        Running will update the progress attributes:
          - load: an estimate of total operations
          - done: a count of load operations completed
          - running: True/False
          - status: arbitrary text for logging
          - ret: the return of a completed run
        '''
        running = self.running
        packet = yield progress


class State(SyncState):
    '''
    A subclass of salt.State.State which implements:
     - async low chunk calling
     - waitfor event requisite
     - fine grained progress reporting
     - a pony
    '''

    def call_chunks(self, chunks):
        '''
        start an event listener
        form chunks into a DAG of requisite dependencies
        iterate from leaves to root order
            create coroutine low chunks
        iterate over events on listener
            put event in a packet
            iterate sending packet to running chunks
            deal with chunk response
        '''

    def call_chunk(self, low, running, chunks):
        '''
        Coroutine accepting events, state returns in an iterable via send()
        interface, yielding a status or return from a completed chunk run.

        Chunks will not run until all requisites have been satisfied. Messages
        accepted via send() interface may contain requisites.
        '''

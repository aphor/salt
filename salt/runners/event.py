# -*- coding: utf-8 -*-
'''
Module for sending events using the runner system.

.. versionadded:: 2016.11.0
'''
from __future__ import absolute_import, print_function, unicode_literals

import logging

import salt.utils.event


log = logging.getLogger(__name__)


def send(tag, data=None):
    '''
    Send an event with the given tag and data.

    This is useful for sending events directly to the master from the shell
    with salt-run. It is also quite useful for sending events in orchestration
    states where the ``fire_event`` requisite isn't sufficient because it does
    not support sending custom data with the event.

    Note that event tags will *not* be namespaced like events sent with the
    ``fire_event`` requisite! Whereas events produced from ``fire_event`` are
    prefixed with ``salt/state_result/<jid>/<minion_id>/<name>``, events sent
    using this runner module will have no such prefix. Make sure your reactors
    don't expect a prefix!

    :param tag: the tag to send with the event
    :param data: an optional dictionary of data to send with the event

    CLI Example:

    .. code-block:: bash

        salt-run event.send my/custom/event '{"foo": "bar"}'

    Orchestration Example:

    .. code-block:: yaml

        # orch/command.sls

        run_a_command:
          salt.function:
            - name: cmd.run
            - tgt: my_minion
            - arg:
              - exit {{ pillar['exit_code'] }}

        send_success_event:
          salt.runner:
            - name: event.send
            - tag: my_event/success
            - data:
                foo: bar
            - require:
              - salt: run_a_command

        send_failure_event:
          salt.runner:
            - name: event.send
            - tag: my_event/failure
            - data:
                baz: qux
            - onfail:
              - salt: run_a_command

    .. code-block:: bash

        salt-run state.orchestrate orch.command pillar='{"exit_code": 0}'
        salt-run state.orchestrate orch.command pillar='{"exit_code": 1}'
    '''
    data = data or {}
    event = salt.utils.event.get_master_event(__opts__, __opts__['sock_dir'],
                                              listen=False)
    return event.fire_event(data, tag)

def waitfor(tag, timeout=300):
    '''
    listen and wait (blocking) for an event with a given tag prefix,
      for (Default timeout=300) seconds.

    This is useful for asynchronous timing in orchestration jobs Where
    prior orchestration states might have asynchronous effects,
    or should wait for an event otherwise outside the orchestration job.

    Hint: redeploy.sh might be a minion upgrade script.

    :param tag: the tag prefix to match, satisfying the waitfor
    :param timeout: seconds before waitfor will raise asyncio.TimeoutError

    Orchestration example:
    .. code-block:: yaml

        # orch/rollout.sls

        prepare for step 1:
          salt.function:
            - name: test.ping
            - tgt: 'minion1'

        step 1:
          salt.function:
            - name: cmd.shell
            - tgt: 'minion1'
            - require:
              - prepare for step 1
            - kwarg:
                bg: False
            - arg:
              - |
                redeploy.sh &&
                salt-call event.send 'rolling/step/1/success'

        step 1 success:
          salt.runner:
            - name: poc.waitfor
            - arg:
              - 'rolling/step/1/success'
            - kwarg:
                timeout: 600

        prepare for step 2:
          salt.function:
            - name: test.ping
            - tgt: 'minion2'
            - require:
              - step 1 success

        step 2:
          salt.function:
            - name: cmd.shell
            - tgt: 'minion2'
            - require:
              - prepare for step 2
            - kwarg:
                bg: False
            - arg:
              - |
                redeploy.sh &&
                salt-call event.send 'rolling/step/2/success'

        step 2 success:
          salt.runner:
            - name: poc.waitfor
            - parallel: True
            - require:
              - prepare for step 2
            - arg:
              - 'rolling/step/2/success'
            - kwarg:
                timeout: 600

        rollout success:
          salt.runner:
            - name: event.send
            - arg:
              - 'rolling/complete'
            - require:
              - step 2 success


    This is also useful to integrate other tools, allowing python or shell
    scripts to block execution waiting for an arbitrary salt event.

    CLI Example:

    .. code-block:: bash

        salt-run event.waitfor rolling/complete timeout=3600

    '''
    opts = __opts__

    events = salt.utils.event.get_master_event(
        opts,
        opts['sock_dir'],
        listen=True)

    events.subscribe(tag=tag)
    events.connect_pull()

    try:
        event_catch = events.get_event(wait=float(timeout), tag=tag)

        if event_catch:
            return True, event_catch

    except asyncio.TimeoutError:
        msg ='timeout waiting {d} seconds for event tag={}'.format(timeout, tag)
        return False, msg

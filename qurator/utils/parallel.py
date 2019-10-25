from multiprocessing import Pool
import gc
import types


def run(tasks, **kwargs):

    if 'processes' in kwargs:

        if kwargs['processes'] == 0:

            if 'initializer' in kwargs:

                if 'initargs' in kwargs:
                    kwargs['initializer'](*kwargs['initargs'])
                else:
                    kwargs['initializer']()

            for ta in tasks:

                ret = ta()

                yield ret

                del ret
                del ta

    with Pool(**kwargs) as pool:

        for it, result in enumerate(pool.imap(_run, tasks)):

            yield result

            del result

            if it % 1000 == 0:
                gc.collect()
    return


def _run(t):

    ret = t()

    del t

    return ret


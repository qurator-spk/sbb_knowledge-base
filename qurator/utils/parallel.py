from multiprocessing import Pool


def run(tasks, **kwargs):

    if 'processes' in kwargs:

        if kwargs['processes'] == 1:

            if 'initializer' in kwargs:

                if 'initargs' in kwargs:
                    kwargs['initializer'](*kwargs['initargs'])
                else:
                    kwargs['initializer']()

            for ta in tasks:
                yield ta()

    with Pool(**kwargs) as pool:

        for result in pool.imap(_run, tasks):

            yield result
    return


def _run(t):

    return t()

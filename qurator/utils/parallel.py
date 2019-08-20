from multiprocessing import Pool


def run(tasks, **kwargs):

    with Pool(**kwargs) as pool:

        for result in pool.imap(_run, tasks):

            yield result
    return


def _run(t):

    return t()

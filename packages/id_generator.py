import random
from django.db import models


def uniqueID():
    random_numbers = [str(random.randint(0, 9)) for _ in range(10)]
    return ''.join(random_numbers)

class UniqueIDField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['unique'] = True
        kwargs['default'] = uniqueID
        kwargs['max_length'] = 100
        super().__init__(*args, **kwargs)


def selfSavingID():
    random_numbers = [str(random.randint(0, 9)) for _ in range(4)]
    return ''.join(random_numbers)


class SelfSavingIDField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['unique'] = False
        kwargs['default'] = selfSavingID
        kwargs['max_length'] = 4
        super().__init__(*args, **kwargs)
               
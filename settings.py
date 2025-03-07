from os import environ

SESSION_CONFIGS = [
    dict(
        name='singleAsset',
        display_name='Single asset: Continuous double auction',
        app_sequence=['singleAsset'],
        num_demo_participants=4,
        market_time=190,
        randomise_types=True,
        short_selling=False,
        margin_buying=True,
        ),
]


# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = ['roleID', 'isObserver', 'isParticipating', 'informed']
SESSION_FIELDS = ['numParticipants']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'es'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'PEN'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
SECRET_KEY = '776841529'

DEMO_PAGE_INTRO_HTML = """ """

INSTALLED_APPS = ['otree']
#DEBUG = False
#AUTH_LEVEL = DEMO

{
    'name': 'Tmtr_exchange',
    'category': 'Technical',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/tmtr_exchange_contact.xml',
        'views/tmtr_exchange_partner.xml',
        'views/tmtr_exchange_counterparty.xml',
        'views/tmtr_exchange_interaction.xml',
        'views/tmtr_exchange_menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
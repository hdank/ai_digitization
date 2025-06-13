{
    'name': 'AI Document Extraction Mixin',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Reusable mixin for AI-powered document extraction',
    'author': 'Custom Development',
    'description': """
AI Document Extraction Mixin
============================
This module provides a reusable mixin that can be injected into any model to enable 
automatic AI document extraction when a PDF/image is uploaded.
    """,
    'depends': ['base', 'mail', 'hr', 'ai'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/ai_extraction_wizard_views.xml',
        'views/ai_document_mixin_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
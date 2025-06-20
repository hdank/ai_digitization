# -*- coding: utf-8 -*-
{
    'name': 'AI Document Extraction',
    'version': '1.0',
    'category': 'Productivity',
    'summary': 'AI-powered document extraction with agent selection',
    'author': 'Leonix',
    'description': """
        This module extends the AI functionality to provide:
        - Agent selection wizard when clicking AI button
        - Custom Gemini 2.0 Flash model support
        - Document extraction capabilities
        - Enhanced chat experience with AI agents
    """,
    'depends': ['base', 'mail', 'ai'],
    'data': [
        'security/ir.model.access.csv',
        'data/ai_agents_data.xml',
        'views/choose_agent_wizard_views.xml',
        'views/ai_agent_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_document_extraction/static/src/js/chatter_ai_patch.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
# -*- coding: utf-8 -*-
{
    'name': "AI Digitization",

    'summary': "AI-powered document digitization using Gemini AI to extract structured data from documents",

    'description': """
AI Digitization Module
======================

This module provides AI-powered document digitization capabilities using Google's Gemini AI model to extract structured information from various document types including handwritten documents, PDFs, invoices, and forms.

Key Features:
* Support for multiple document types (handwritten, printed PDFs, invoices, forms)
* Predefined prompt templates for common document types
* Custom prompt support for specialized use cases
* Integration with Google Gemini AI (gemini-2.0-flash model)
* Automatic field mapping to Odoo models
* Structured JSON data extraction
* Record creation in target Odoo models

Supported Document Types:
* Handwritten documents
* Printed PDFs
* Invoices
* Forms
* Mixed content documents
* Custom document types
    """,

    'author': "AI Development Team",
    'website': "https://www.yourcompany.com",

    'category': 'Tools',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/document_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_digitization/static/src/js/form_refresh.js',
        ],
    },
}


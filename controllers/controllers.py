# -*- coding: utf-8 -*-
# from odoo import http


# class AiDigitization(http.Controller):
#     @http.route('/ai_digitization/ai_digitization', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ai_digitization/ai_digitization/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ai_digitization.listing', {
#             'root': '/ai_digitization/ai_digitization',
#             'objects': http.request.env['ai_digitization.ai_digitization'].search([]),
#         })

#     @http.route('/ai_digitization/ai_digitization/objects/<model("ai_digitization.ai_digitization"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ai_digitization.object', {
#             'object': obj
#         })


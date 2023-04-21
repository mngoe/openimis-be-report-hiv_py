from distutils.command import upload
from reporthiv.models import invoice_hiv_query

from reporthiv.report_templates import rptInvoicePerProgram

report_definitions = [ 
    {
        "name": "invoice_fosa_hiv",
        "engine": 0,
        "default_report":rptInvoicePerProgram.template,
        "description": "Etat de paiement par fosa",
        "module": "reporthiv",
        "python_query": invoice_hiv_query, 
        "permission": ["131215"],
    }
]
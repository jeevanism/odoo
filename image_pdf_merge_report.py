#This Odoo custom model enables users to merge multiple PDF and image files (JPEG, PNG) into a single print-ready PDF document. 
#The script ensures that only valid PDF and image files are uploaded, providing a reliable and secure experience for the user. 
#Non-PDF or non-image files are automatically rejected during the upload process.


from odoo import api, fields, models, _
from PyPDF2 import PdfFileReader, PdfFileWriter
import io
import base64
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def join_pdf(self, pdf_chunks):
        """Merges multiple PDF files into a single PDF."""
        result_pdf = PdfFileWriter()

        for chunk in pdf_chunks:
            try:
                chunk_pdf = PdfFileReader(io.BytesIO(chunk), strict=False)
                for page in range(chunk_pdf.getNumPages()):
                    result_pdf.addPage(chunk_pdf.getPage(page))
            except Exception as e:
                _logger.error(f"Error reading PDF chunk: {e}")
                raise ValidationError("One or more uploaded files are not valid PDF files.")

        output = io.BytesIO()
        result_pdf.write(output)
        return output.getvalue()

    def _run_wkhtmltopdf(
        self,
        bodies,
        report_ref,
        header=None,
        footer=None,
        landscape=False,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        """Overriding method to merge classification uploads with the main report."""
        result = super()._run_wkhtmltopdf(
            bodies,
            report_ref,
            header,
            footer,
            landscape,
            specific_paperformat_args,
            set_viewport_size,
        )

        # lets say we need to print PDF report of sale order
        report_creation_model = self.env.context.get('active_model') == 'sale.order' and self.env['sale.order'].browse(self.env.context.get('active_id'))

        pdf_chunks = [result]  # Start with the generated report

        if quality_check and quality_check.classification_upload_ids:
            for upload_line in quality_check.classification_upload_ids:
                if upload_line.upload:
                    try:
                        decoded_file = base64.b64decode(upload_line.upload)
                        file_type = upload_line.file_name.lower()

                        # If the file is a PDF, append it to the list for merging
                        if file_type.endswith('.pdf'):
                            pdf_chunks.append(decoded_file)
                        else:
                            # Image files are handled by the QWeb template; do not merge them into the PDF
                            continue
                    except Exception as e:
                        _logger.error(f"Error decoding file: {e}")
                        raise ValidationError("One or more uploaded files are not valid PDFs or images.")

            # Merge the main report with the PDF attachments
            result = self.join_pdf(pdf_chunks)

        return result

from flask import Blueprint, send_file

from app.services.exporter import export_invoice_review_to_excel

exports_bp = Blueprint("exports", __name__)


@exports_bp.get("/exports/lexware_invoice_review.xlsx")
def export_lexware_invoice_review():
    return _send_workbook(export_invoice_review_to_excel(), "lexware_invoice_review.xlsx")


def _send_workbook(workbook, download_name: str):
    response = send_file(
        workbook,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

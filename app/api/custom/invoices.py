from flask import Blueprint
from flask_rest_jsonapi.exceptions import ObjectNotFound
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy.orm.exc import NoResultFound


from app.api.auth import return_file
from app.api.helpers.errors import ForbiddenError, NotFoundError
from app.api.helpers.order import create_pdf_tickets_for_holder
from app.api.helpers.storage import UPLOAD_PATHS, generate_hash
from app.models.order import Order
from app.models.event_invoice import EventInvoice
from app.api.custom.orders import order_blueprint

event_blueprint = Blueprint('event_blueprint', __name__, url_prefix='/v1/events')


@event_blueprint.route('/invoices/<string:invoice_identifier>')
@jwt_required
def event_invoices(invoice_identifier):
    if not current_user:
        return ForbiddenError({'source': ''}, 'Authentication Required to access Invoice').respond()
    try:
        event_invoice = EventInvoice.query.filter_by(identifier=invoice_identifier).first()
        event_id = event_invoice.event_id
    except NoResultFound:
        return NotFoundError({'source': ''}, 'Event Invoice not found').respond()
    if not current_user.is_organizer(event_id) and not current_user.is_staff:
        return ForbiddenError({'source': ''}, 'Unauthorized Access').respond()
    key = UPLOAD_PATHS['pdf']['event_invoices'].format(identifier=invoice_identifier)
    file_path = '../generated/invoices/{}/{}/'.format(key, generate_hash(key)) + invoice_identifier + '.pdf'
    try:
        return return_file('event-invoice', file_path, invoice_identifier)
    except FileNotFoundError:
        raise ObjectNotFound({'source': ''},
                             "The Event Invoice isn't available at the moment. \
                             Invoices are usually issued on the 1st of every month")


@order_blueprint.route('/invoices/<string:order_identifier>')
@jwt_required
def order_invoices(order_identifier):
    if current_user:
        try:
            order = Order.query.filter_by(identifier=order_identifier).first()
        except NoResultFound:
            return NotFoundError({'source': ''}, 'Order Invoice not found').respond()
        if current_user.can_download_tickets(order):
            key = UPLOAD_PATHS['pdf']['order'].format(identifier=order_identifier)
            file_path = '../generated/invoices/{}/{}/'.format(key, generate_hash(key)) + order_identifier + '.pdf'
            try:
                return return_file('invoice', file_path, order_identifier)
            except FileNotFoundError:
                create_pdf_tickets_for_holder(order)
                return return_file('invoice', file_path, order_identifier)
        else:
            return ForbiddenError({'source': ''}, 'Unauthorized Access').respond()
    else:
        return ForbiddenError({'source': ''}, 'Authentication Required to access Invoice').respond()

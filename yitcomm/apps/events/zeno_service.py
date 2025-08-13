# services/zenopay_service.py
import requests
import logging
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ZenoPayService:
    """Service class to handle ZenoPay API integration for mobile money payments"""

    def __init__(self):
        self.base_url = "https://zenoapi.com/api/payments"
        self.api_key = getattr(settings, 'ZENOPAY_APIKEY', '')
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key
        }

    def initiate_payment(self, registration) -> Tuple[bool, Dict]:
        """
        Initiate payment for an event registration

        Args:
            registration: EventRegistration instance

        Returns:
            Tuple of (success: bool, response_data: dict)
        """
        logger.info(f"Initiating payment for registration {registration.id}")
        try:
            # Validate registration
            if registration.event.is_free:
                return False, {'error': 'Cannot initiate payment for free event'}

            if not registration.payment_order_id:
                logger.warning(f"No payment order ID found for registration {registration.id}")
                return False, {'error': 'No payment order ID found'}

            # Prepare payment payload
            payload = {
                "order_id": registration.payment_order_id,
                "buyer_email": registration.user.email,
                "buyer_name": registration.user.get_full_name(),
                "buyer_phone": self._format_phone_number(registration.user.phone_number),
                "amount": int(registration.event.price)  # Convert to integer (TZS cents)
            }
            logger.info(f"Preparing payment payload: {payload} ===========================================")
            logger.info(f"Payment payload: {payload}")

            # Make API request
            response = requests.post(
                f"{self.base_url}/mobile_money_tanzania",
                headers=self.headers,
                json=payload,
                timeout=300
            )

        
            response_data = response.json()
            logger.info(f"ZenoPay response: {response_data.get('status_code')} - {response_data.get('text')} ==============================")

            if response.status_code == 200 and response_data.get('status') == 'success':
                # Update registration with payment details
                registration.payment_status = 'processing'
                registration.payment_phone = payload['buyer_phone']
                registration.save()

                # Create payment transaction record
                from .models import PaymentTransaction
                transaction = PaymentTransaction.objects.create(
                    registration=registration,
                    order_id=registration.payment_order_id,
                    amount=registration.event.price,
                    phone_number=payload['buyer_phone'],
                    status='pending',
                    api_response=response_data
                )

                logger.info(f"Payment initiated successfully for order {registration.payment_order_id}")

                return True, {
                    'success': True,
                    'message': response_data.get('message', 'Payment initiated successfully'),
                    'order_id': registration.payment_order_id,
                    'transaction_id': transaction.id
                }

            else:
                logger.error(f"Payment initiation failed: {response_data}")

                # Mark registration as failed
                registration.payment_status = 'failed'
                registration.save()

                return False, {
                    'success': False,
                    'error': response_data.get('message', 'Payment initiation failed')
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during payment initiation: {str(e)}")
            return False, {'success': False, 'error': 'Network error occurred'}

        except Exception as e:
            logger.error(f"Unexpected error during payment initiation: {str(e)}")
            return False, {'success': False, 'error': 'An unexpected error occurred'}

    def check_payment_status(self, order_id: str) -> Tuple[bool, Dict]:
        """
        Check the status of a payment order

        Args:
            order_id: The payment order ID

        Returns:
            Tuple of (success: bool, response_data: dict)
        """
        try:
            # Make API request to check status
            response = requests.get(
                f"{self.base_url}/order-status",
                headers=self.headers,
                params={'order_id': order_id},
                timeout=30
            )

            response_data = response.json()

            if response.status_code == 200 and response_data.get('result') == 'SUCCESS':
                data = response_data.get('data', [])
                if data:
                    payment_info = data[0]
                    return True, {
                        'success': True,
                        'payment_status': payment_info.get('payment_status'),
                        'transaction_id': payment_info.get('transid'),
                        'reference': payment_info.get('reference'),
                        'channel': payment_info.get('channel'),
                        'amount': payment_info.get('amount'),
                        'creation_date': payment_info.get('creation_date'),
                        'msisdn': payment_info.get('msisdn')
                    }

            logger.warning(f"Payment status check failed for order {order_id}: {response_data}")
            return False, {'success': False, 'error': 'Could not retrieve payment status'}

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during payment status check: {str(e)}")
            return False, {'success': False, 'error': 'Network error occurred'}

        except Exception as e:
            logger.error(f"Unexpected error during payment status check: {str(e)}")
            return False, {'success': False, 'error': 'An unexpected error occurred'}

    def process_callback(self, callback_data: Dict) -> Tuple[bool, str]:
        """
        Process payment callback from ZenoPay

        Args:
            callback_data: Callback data from ZenoPay

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            order_id = callback_data.get('order_id')
            payment_status = callback_data.get('payment_status', '').upper()

            if not order_id:
                return False, 'No order ID in callback data'

            # Find the registration and transaction
            from .models import EventRegistration, PaymentTransaction

            try:
                registration = EventRegistration.objects.get(payment_order_id=order_id)
                transaction = PaymentTransaction.objects.get(order_id=order_id)
            except (EventRegistration.DoesNotExist, PaymentTransaction.DoesNotExist):
                logger.error(f"Registration or transaction not found for order {order_id}")
                return False, 'Order not found'

            # Update transaction with callback data
            transaction.callback_data = callback_data

            if payment_status == 'COMPLETED':
                # Mark payment as completed
                transaction.mark_completed(callback_data)

                logger.info(f"Payment completed successfully for order {order_id}")
                return True, 'Payment processed successfully'

            elif payment_status in ['FAILED', 'CANCELLED', 'EXPIRED']:
                # Mark payment as failed
                transaction.mark_failed(f"Payment {payment_status.lower()}")

                logger.warning(f"Payment {payment_status.lower()} for order {order_id}")
                return True, f'Payment {payment_status.lower()}'

            else:
                # Update status but don't mark as completed/failed yet
                transaction.status = 'pending'
                transaction.save()

                logger.info(f"Payment status update for order {order_id}: {payment_status}")
                return True, 'Payment status updated'

        except Exception as e:
            logger.error(f"Error processing payment callback: {str(e)}")
            return False, 'Error processing callback'

    def _format_phone_number(self, phone: str) -> str:
        """
        Format phone number for Tanzania mobile money
        Expected format: 07XXXXXXXX

        Args:
            phone: Phone number in various formats

        Returns:
            Formatted phone number
        """
        if not phone:
            return ''

        # Remove any non-digit characters
        phone = ''.join(filter(str.isdigit, phone))

        # Handle different formats
        if phone.startswith('255'):
            # Convert from +255XXXXXXXXX to 07XXXXXXXX
            phone = '0' + phone[3:]
        elif phone.startswith('7') and len(phone) == 9:
            # Convert from 7XXXXXXXX to 07XXXXXXXX
            phone = '0' + phone
        elif not phone.startswith('0'):
            # Add leading zero if missing
            phone = '0' + phone

        # Validate format
        if len(phone) != 10 or not phone.startswith('07'):
            logger.warning(f"Invalid phone number format: {phone}")
            return phone

        return phone

    def get_supported_payment_methods(self) -> list:
        """Get list of supported payment methods"""
        return [
            'M-Pesa Tanzania',
            'Tigo Pesa',
            'Airtel Money',
            'Halopesa'
        ]


# Utility functions for views
def create_payment_for_registration(registration):
    """
    Create and initiate payment for an event registration

    Args:
        registration: EventRegistration instance

    Returns:
        Dict with success status and message
    """
    if registration.event.is_free:
        return {
            'success': False,
            'error': 'This is a free event, no payment required'
        }

    if registration.payment_status in ['completed', 'processing']:
        return {
            'success': False,
            'error': 'Payment already processed or in progress'
        }

    # Initialize ZenoPay service
    zenopay = ZenoPayService()
    success, result = zenopay.initiate_payment(registration)

    return result


def check_and_update_payment_status(registration):
    """
    Check and update payment status for a registration

    Args:
        registration: EventRegistration instance

    Returns:
        Dict with payment status information
    """
    if not registration.payment_order_id:
        return {'success': False, 'error': 'No payment order found'}

    zenopay = ZenoPayService()
    success, result = zenopay.check_payment_status(registration.payment_order_id)

    if success:
        # Update registration based on payment status
        payment_status = result.get('payment_status', '').upper()

        if payment_status == 'COMPLETED' and registration.payment_status != 'completed':
            # Update registration as completed
            from .models import PaymentTransaction
            try:
                transaction = PaymentTransaction.objects.get(order_id=registration.payment_order_id)
                transaction.mark_completed(result)
            except PaymentTransaction.DoesNotExist:
                # Create transaction record if it doesn't exist
                PaymentTransaction.objects.create(
                    registration=registration,
                    order_id=registration.payment_order_id,
                    amount=registration.event.price,
                    status='completed',
                    api_response=result
                ).mark_completed(result)

    return result
"""Testes das notificações para os donos do mercadinho."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import BusinessConfig
from app.core.notifications.notify_owner import notify_new_order, notify_sale_confirmed
from app.models.order import Order, OrderStatus


def make_business(dono_1: str = "+5571991110001", dono_2: str = "+5571992220002") -> BusinessConfig:
    return BusinessConfig(
        {
            "notificacao": {
                "whatsapp_dono_1": dono_1,
                "whatsapp_dono_2": dono_2,
                "valor_alto": 100,
                "comissao_percentual": 5.0,
            }
        }
    )


def make_order(total: float = 50.0, with_items: bool = True, delivery: bool = True) -> Order:
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.total_amount = total
    order.delivery_building_block = "A" if delivery else None
    order.delivery_apartment = "201" if delivery else None
    order.status = OrderStatus.PENDING

    if with_items:
        item = MagicMock()
        item.product_name = "Coca-Cola 2L"
        item.quantity = 2
        item.subtotal = total
        order.items = [item]
    else:
        order.items = []

    return order


class TestNotifyNewOrder:
    async def test_notifica_dono_1(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_new_order(order, "5571999990001", "Maria", whatsapp=wa, business=business)

        wa.send_text.assert_called_once()
        phone_called = wa.send_text.call_args[0][0]
        assert phone_called == "5571991110001"

    async def test_nao_notifica_dono_2(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_new_order(order, "5571999990001", "Maria", whatsapp=wa, business=business)

        for call in wa.send_text.call_args_list:
            assert "5571992220002" not in call[0][0]

    async def test_mensagem_contem_total(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business()
        order = make_order(total=75.00)

        await notify_new_order(order, "5571999990001", "João", whatsapp=wa, business=business)

        msg = wa.send_text.call_args[0][1]
        assert "75,00" in msg or "75.00" in msg

    async def test_pedido_alto_tem_alerta(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business()
        order = make_order(total=150.00)

        await notify_new_order(order, "5571999990001", "Cliente VIP", whatsapp=wa, business=business)

        msg = wa.send_text.call_args[0][1]
        assert "ALTO" in msg or "🚨" in msg

    async def test_dono_1_todo_nao_envia(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business(dono_1="TODO")
        order = make_order()

        await notify_new_order(order, "5571999990001", "Maria", whatsapp=wa, business=business)

        wa.send_text.assert_not_called()

    async def test_retirada_no_balcao(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        business = make_business()
        order = make_order(delivery=False)

        await notify_new_order(order, "5571999990001", "Carlos", whatsapp=wa, business=business)

        msg = wa.send_text.call_args[0][1]
        assert "Retirada" in msg or "balcão" in msg


class TestNotifySaleConfirmed:
    async def test_notifica_ambos_donos(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_sale_confirmed(order, "5571999990001", "Ana", 2.50, whatsapp=wa, business=business)

        assert wa.send_text.call_count == 2
        phones = [call[0][0] for call in wa.send_text.call_args_list]
        assert "5571991110001" in phones
        assert "5571992220002" in phones

    async def test_dono_1_recebe_audio_primeiro(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_sale_confirmed(order, "5571999990001", "Ana", 2.50, whatsapp=wa, business=business)

        wa.send_audio_url.assert_called_once()
        audio_phone = wa.send_audio_url.call_args[0][0]
        assert audio_phone == "5571991110001"

    async def test_dono_2_nao_recebe_audio(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_sale_confirmed(order, "5571999990001", "Ana", 2.50, whatsapp=wa, business=business)

        assert wa.send_audio_url.call_count == 1

    async def test_mensagem_contem_comissao(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business()
        order = make_order(total=100.00)

        await notify_sale_confirmed(order, "5571999990001", "Pedro", 5.00, whatsapp=wa, business=business)

        msg = wa.send_text.call_args_list[0][0][1]
        assert "5,00" in msg or "5.00" in msg
        assert "Comissão" in msg or "comissão" in msg

    async def test_dono_2_todo_nao_envia_para_dono_2(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business(dono_2="TODO")
        order = make_order()

        await notify_sale_confirmed(order, "5571999990001", "Ana", 2.50, whatsapp=wa, business=business)

        assert wa.send_text.call_count == 1
        assert wa.send_text.call_args[0][0] == "5571991110001"

    async def test_mensagem_contem_confirmado(self):
        wa = AsyncMock()
        wa.send_text = AsyncMock(return_value=True)
        wa.send_audio_url = AsyncMock(return_value=True)
        business = make_business()
        order = make_order()

        await notify_sale_confirmed(order, "5571999990001", "Lúcia", 2.50, whatsapp=wa, business=business)

        msg = wa.send_text.call_args_list[0][0][1]
        assert "CONFIRMADA" in msg or "confirmada" in msg.lower()

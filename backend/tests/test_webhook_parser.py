"""Testes do parser de webhook da Evolution API."""

import pytest

from app.core.whatsapp.types import WhatsAppMessageType
from app.core.whatsapp.webhook_parser import parse_webhook


def make_payload(
    event: str = "messages.upsert",
    remote_jid: str = "5571999990001@s.whatsapp.net",
    from_me: bool = False,
    text: str = "Olá",
    push_name: str = "João",
) -> dict:
    return {
        "event": event,
        "data": {
            "key": {
                "remoteJid": remote_jid,
                "fromMe": from_me,
                "id": "ABCD1234",
            },
            "pushName": push_name,
            "messageTimestamp": 1700000000,
            "message": {"conversation": text},
        },
    }


class TestParseWebhook:
    def test_parseia_mensagem_texto(self):
        msg = parse_webhook(make_payload(text="Quero pedir"))
        assert msg is not None
        assert msg.text == "Quero pedir"
        assert msg.message_type == WhatsAppMessageType.TEXT

    def test_normaliza_telefone(self):
        msg = parse_webhook(make_payload(remote_jid="5571999990001@s.whatsapp.net"))
        assert msg is not None
        assert msg.phone == "5571999990001"
        assert msg.e164 == "+5571999990001"

    def test_extrai_nome_push(self):
        msg = parse_webhook(make_payload(push_name="Maria"))
        assert msg is not None
        assert msg.name == "Maria"

    def test_ignora_mensagem_propria(self):
        msg = parse_webhook(make_payload(from_me=True))
        assert msg is None

    def test_ignora_evento_nao_mensagem(self):
        msg = parse_webhook(make_payload(event="qr.updated"))
        assert msg is None

    def test_ignora_grupo(self):
        msg = parse_webhook(make_payload(remote_jid="12345@g.us"))
        assert msg is None

    def test_parseia_texto_extendido(self):
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "5571111@s.whatsapp.net", "fromMe": False, "id": "X1"},
                "pushName": "Teste",
                "messageTimestamp": 1700000000,
                "message": {"extendedTextMessage": {"text": "Olá, tem coca-cola?"}},
            },
        }
        msg = parse_webhook(payload)
        assert msg is not None
        assert msg.text == "Olá, tem coca-cola?"

    def test_ignora_payload_vazio(self):
        msg = parse_webhook({"event": "messages.upsert", "data": {}})
        assert msg is None

    def test_audio_retorna_tipo_audio(self):
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "5571111@s.whatsapp.net", "fromMe": False, "id": "A1"},
                "pushName": "Fulano",
                "messageTimestamp": 1700000000,
                "message": {"audioMessage": {"url": "https://..."}},
            },
        }
        msg = parse_webhook(payload)
        assert msg is not None
        assert msg.message_type == WhatsAppMessageType.AUDIO
        assert msg.text == ""

    def test_message_received_event(self):
        payload = make_payload(event="message.received")
        msg = parse_webhook(payload)
        assert msg is not None


class TestInboundMessage:
    def test_is_text_verdadeiro(self):
        msg = parse_webhook(make_payload())
        assert msg is not None
        assert msg.is_text() is True

    def test_is_text_falso_para_audio(self):
        payload = {
            "event": "messages.upsert",
            "data": {
                "key": {"remoteJid": "5571111@s.whatsapp.net", "fromMe": False, "id": "A1"},
                "pushName": None,
                "messageTimestamp": 1700000000,
                "message": {"audioMessage": {}},
            },
        }
        msg = parse_webhook(payload)
        assert msg is not None
        assert msg.is_text() is False

"""Mock of AeroParts Imports' partner pricing service (SOAP 1.1, document/literal).

Stands in for the supplier's real system so the price-sync integration can be built and
tested end to end. Standard library only, like many small legacy supplier endpoints.

  GET  /PartnerPriceService?wsdl   -> WSDL
  POST /PartnerPriceService        -> GetPriceList(accountId)

Run:  python -m integration.supplier_soap_service   (listens on :8765)
"""

import os
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.sax.saxutils import escape

NS = "urn:aeroparts:pricing:v1"
SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
PATH = "/PartnerPriceService"
VALID_ACCOUNTS = {"SKYF-0042"}
PRICE_LIST_ID = "AP-PL-2026Q4"

# This quarter's price list. Values differ from SkyForge's migrated prices on purpose.
PRICE_LIST = [
    # partNo, description, unitPrice (INR), leadTimeDays
    ("AP-BLM-2306-2450", "Brushless motor 2306 2450KV", 1450.00, 28),   # unchanged
    ("AP-BLM-3508-0700", "Brushless motor 3508 700KV", 3350.00, 28),    # +4.7%
    ("AP-ESC-B32-30", "ESC 30A BLHeli_32", 1020.00, 35),                # +7.4%, lead time 28 -> 35
    ("AP-ESC-B32-40", "ESC 40A BLHeli_32", 1350.00, 28),                # unchanged
    ("AP-FC-F722", "Flight controller F722", 6650.00, 28),              # -2.2%
    ("AP-FC-H743", "Flight controller H743", 16900.00, 28),             # +47%: should be held for review
    ("AP-GNSS-M10", "GNSS module M10", 2250.00, 28),                    # +7.1%
    ("AP-BLM-2207-1950", "Brushless motor 2207 1950KV", 1290.00, 21),   # SkyForge doesn't stock this
    # AP-RX-ELRS24 intentionally absent: not on this quarter's list
]

WSDL = f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions name="PartnerPriceService" targetNamespace="{NS}" xmlns:tns="{NS}"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns="http://schemas.xmlsoap.org/wsdl/">
  <types>
    <xsd:schema targetNamespace="{NS}" elementFormDefault="qualified">
      <xsd:element name="GetPriceList">
        <xsd:complexType><xsd:sequence>
          <xsd:element name="accountId" type="xsd:string"/>
        </xsd:sequence></xsd:complexType>
      </xsd:element>
      <xsd:complexType name="PriceLine"><xsd:sequence>
        <xsd:element name="partNo" type="xsd:string"/>
        <xsd:element name="description" type="xsd:string"/>
        <xsd:element name="unitPrice" type="xsd:decimal"/>
        <xsd:element name="currency" type="xsd:string"/>
        <xsd:element name="leadTimeDays" type="xsd:int"/>
        <xsd:element name="validFrom" type="xsd:date"/>
      </xsd:sequence></xsd:complexType>
      <xsd:element name="GetPriceListResponse">
        <xsd:complexType><xsd:sequence>
          <xsd:element name="priceListId" type="xsd:string"/>
          <xsd:element name="line" type="tns:PriceLine" minOccurs="0" maxOccurs="unbounded"/>
        </xsd:sequence></xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>
  <message name="GetPriceListRequest"><part name="parameters" element="tns:GetPriceList"/></message>
  <message name="GetPriceListResponseMessage"><part name="parameters" element="tns:GetPriceListResponse"/></message>
  <portType name="PricePort">
    <operation name="GetPriceList">
      <input message="tns:GetPriceListRequest"/>
      <output message="tns:GetPriceListResponseMessage"/>
    </operation>
  </portType>
  <binding name="PriceBinding" type="tns:PricePort">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="GetPriceList">
      <soap:operation soapAction="{NS}#GetPriceList"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>
  <service name="PartnerPriceService">
    <port name="PricePort" binding="tns:PriceBinding"><soap:address location="{{location}}"/></port>
  </service>
</definitions>"""


def envelope(body: str) -> bytes:
    return (f'<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="{SOAP_ENV}">'
            f"<soap:Body>{body}</soap:Body></soap:Envelope>").encode()


def fault(code: str, message: str) -> bytes:
    return envelope(f"<soap:Fault><faultcode>soap:{code}</faultcode>"
                    f"<faultstring>{escape(message)}</faultstring></soap:Fault>")


def price_list_response(valid_from="2026-10-01") -> bytes:
    lines = "".join(
        f"<tns:line><tns:partNo>{p}</tns:partNo><tns:description>{escape(d)}</tns:description>"
        f"<tns:unitPrice>{price:.2f}</tns:unitPrice><tns:currency>INR</tns:currency>"
        f"<tns:leadTimeDays>{lead}</tns:leadTimeDays><tns:validFrom>{valid_from}</tns:validFrom></tns:line>"
        for p, d, price, lead in PRICE_LIST)
    return envelope(f'<tns:GetPriceListResponse xmlns:tns="{NS}">'
                    f"<tns:priceListId>{PRICE_LIST_ID}</tns:priceListId>{lines}</tns:GetPriceListResponse>")


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype="text/xml; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == PATH and "wsdl" in self.path.lower():
            host = self.headers.get("Host", f"localhost:{self.server.server_port}")
            return self._send(200, WSDL.replace("{location}", f"http://{host}{PATH}").encode())
        self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != PATH:
            return self._send(404, b"not found", "text/plain")
        if os.getenv("AEROPARTS_MAINTENANCE"):                   # simulate supplier outage
            return self._send(503, fault("Server", "Service under maintenance"))
        try:
            root = ET.fromstring(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            req = root.find(f".//{{{NS}}}GetPriceList")
            account = req.findtext(f"{{{NS}}}accountId") if req is not None else None
        except ET.ParseError:
            return self._send(500, fault("Client", "Malformed SOAP request"))
        if req is None:
            return self._send(500, fault("Client", "Unsupported operation"))
        if account not in VALID_ACCOUNTS:
            return self._send(500, fault("Client", f"Unknown partner account '{account}'"))
        self._send(200, price_list_response())

    def log_message(self, fmt, *args):   # keep test output quiet
        pass


def serve(port=8765):
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    srv = serve(int(os.getenv("AEROPARTS_PORT", 8765)))
    print(f"AeroParts PartnerPriceService on http://127.0.0.1:{srv.server_port}{PATH}?wsdl")
    srv.serve_forever()

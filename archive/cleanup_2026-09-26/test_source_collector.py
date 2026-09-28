"""Run with:  python tests/test_source_collector.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from source_collector import parse_products, guess_model  # noqa: E402


def mock_page():
    inner = (
        '{"id":"gid://shopify/Product/1","variantId":"gid://shopify/ProductVariant/1",'
        '"handle":"von-vrb-247nrak-bottom-mount-freezer-247l-black-inox",'
        '"name":"VON VRB-247NRAK Bottom Mount Freezer 247L - Black Inox","image":"https://x/y.png",'
        '"price":77995,"originalPrice":"$undefined","rating":4,"reviewCount":0,"badge":"$undefined",'
        '"brand":"Von","subCategory":"Combination (Bottom Mount Freezer)","features":["A \\u0026 B"]},'
        '{"id":"gid://shopify/Product/2","variantId":"gid://shopify/ProductVariant/2",'
        '"handle":"hisense-rq-78wc4sa-4-door-fridge-615l",'
        '"name":"Hisense RQ-78WC4SA 4 Door Fridge - 615L","image":"https://x/z.webp",'
        '"price":359995,"originalPrice":419995,"rating":4,"reviewCount":0,"badge":"$undefined",'
        '"brand":"Hisense","subCategory":"4 Door","features":["PureView"]}'
    )
    # duplicate of the first product appears again later in the page
    dup = inner.split("},{")[0] + "}"
    return ("<html><script>self.__next_f.push([1," + json.dumps(inner) + "])</script>"
            "<script>self.__next_f.push([1," + json.dumps(dup) + "])</script></html>")


def main():
    products = parse_products(mock_page())
    assert len(products) == 2, products
    a, b = products
    assert a["price"] == 77995 and a["original_price"] is None and a["model"] == "VRB-247NRAK"
    assert b["price"] == 359995 and b["original_price"] == 419995 and b["model"] == "RQ-78WC4SA"
    assert b["brand"] == "Hisense"
    assert guess_model("Hisense H13DX Dishwasher 13 Place Setting - Silver") == "H13DX"
    assert guess_model("Von 10Kg Front Load Washing Machine 1400RPM (VWM-106FDDSX)") == "VWM-106FDDSX"
    assert guess_model("Hisense 43A6Q UHD VIDAA Smart 4K TV") == "43A6Q"
    assert guess_model("Plain kettle 1.7L", "plain-kettle") == "plain-kettle"
    print("All parser tests passed.")


if __name__ == "__main__":
    main()

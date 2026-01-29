TAG_NAME_TO_MAC = {
    "Tag1": "B827EB0F88D0",
    "Wasza_szerokosc":"DCA632F1D88D",
    "Maciej P": "AABBCCDDEE01",
    "Gruby": "AABBCCDDEE02",
    "Chudy": "AABBCCDDEE03",
    "Julek": "AABBCCDDEE04",
    "Ta co ogarnia co się dzieje w firmie": "AABBCCDDEE05",
}

TAG_MAC_TO_NAME = {v: k for k, v in TAG_NAME_TO_MAC.items()}


def get_mac_by_name(tag_name: str) -> str:
    return TAG_NAME_TO_MAC.get(tag_name)


def get_name_by_mac(mac_address: str) -> str:
    return TAG_MAC_TO_NAME.get(mac_address, mac_address)


def get_all_tags():
    return [{"name": name, "mac": mac} for name, mac in TAG_NAME_TO_MAC.items()]

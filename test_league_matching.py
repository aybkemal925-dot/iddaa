#!/usr/bin/env python3
from iddaapro import lig_filtreli_key, lig_key


def run_case(found: str, selected: str, expected: bool) -> None:
    result = lig_filtreli_key(found, {selected})
    assert result == expected, (
        f"expected={expected} found={found!r} selected={selected!r} got={result}"
    )


def main() -> None:
    turkey_super = lig_key("TURKIYE", "Süper Lig")
    turkey_first = lig_key("TURKIYE", "1. Lig")
    england_one = lig_key("INGILTERE", "1. Lig")

    # Eslestirme artik isim benzerliginden degil, ayni ulke + ayni seviye mantigindan gider.
    run_case("turkiye Spor Toto Super Lig", turkey_super, True)
    run_case("turkiye Turkcell Super Lig", turkey_super, True)
    run_case("turkiye TFF 1 Lig", turkey_first, True)
    run_case("turkiye Bank Asya 1 Lig", turkey_first, True)
    run_case("turkiye 2 Lig", turkey_super, False)
    run_case("turkiye 4 Lig", turkey_first, False)
    run_case("ingiltere League One", england_one, True)
    run_case("ingiltere Championship", england_one, False)

    print("league matching tests passed")


if __name__ == "__main__":
    main()

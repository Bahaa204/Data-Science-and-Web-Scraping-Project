import os, re

HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


countries = [
    ("United States", "us", "us", "en-US"),
    ("United Kingdom", "uk", "uk", "en-GB"),
    ("Canada", "ca-en", "ca", "en-CA"),
    ("Australia", "au", "au", "en-AU"),
    ("New Zealand", "nz", "nz", "en-NZ"),
    ("Ireland", "ie", "ie", "en-IE"),
    ("South Africa", "za-en", "za", "en-ZA"),
    ("Lebanon", "lb-en", "lb", "en-LB"),
    ("United Arab Emirates", "ae-en", "ae", "en-AE"),
    ("Saudi Arabia", "sa-en", "sa", "en-SA"),
    ("Qatar", "qa-en", "qa", "en-QA"),
    ("Kuwait", "kw-en", "kw", "en-KW"),
    ("Bahrain", "bh-en", "bh", "en-BH"),
    ("Oman", "om-en", "om", "en-OM"),
    ("Jordan", "jo-en", "jo", "en-JO"),
    ("Egypt", "eg-en", "eg", "en-EG"),
    ("Morocco", "ma-en", "ma", "en-MA"),
    ("Tunisia", "tn-en", "tn", "en-TN"),
    ("Algeria", "dz-en", "dz", "en-DZ"),
    ("Israel", "il-en", "il", "en-IL"),
    ("India", "in-en", "in", "en-IN"),
    ("Pakistan", "pk-en", "pk", "en-PK"),
    ("Bangladesh", "bd-en", "bd", "en-BD"),
    ("Sri Lanka", "lk-en", "lk", "en-LK"),
    ("Nepal", "np-en", "np", "en-NP"),
    ("Bhutan", "bt-en", "bt", "en-BT"),
    ("Maldives", "mv-en", "mv", "en-MV"),
    ("Singapore", "sg-en", "sg", "en-SG"),
    ("Malaysia", "my-en", "my", "en-MY"),
    ("Philippines", "ph-en", "ph", "en-PH"),
    ("Indonesia", "id-en", "id", "en-ID"),
    ("Thailand", "th-en", "th", "en-TH"),
    ("Vietnam", "vn-en", "vn", "en-VN"),
    ("Cambodia", "kh-en", "kh", "en-KH"),
    ("Laos", "la-en", "la", "en-LA"),
    ("Myanmar", "mm-en", "mm", "en-MM"),
    ("Brunei", "bn-en", "bn", "en-BN"),
    ("Japan", "jp-ja", "jp", "ja-JP"),
    ("South Korea", "kr-en", "kr", "en-KR"),
    ("Hong Kong", "hk-en", "hk", "en-HK"),
    ("Taiwan", "tw-en", "tw", "en-TW"),
    ("Macau", "mo-en", "mo", "en-MO"),
    ("Kazakhstan", "kz-en", "kz", "en-KZ"),
    ("Azerbaijan", "az-en", "az", "en-AZ"),
    ("Georgia", "ge-en", "ge", "en-GE"),
    ("Armenia", "am-en", "am", "en-AM"),
    ("Uzbekistan", "uz-en", "uz", "en-UZ"),
    ("Kyrgyzstan", "kg-en", "kg", "en-KG"),
    ("Tajikistan", "tj-en", "tj", "en-TJ"),
    ("Mongolia", "mn-en", "mn", "en-MN"),
    ("Germany", "de-en", "de", "en-DE"),
    ("France", "fr", "fr", "fr-FR"),
    ("Spain", "es", "es", "es-ES"),
    ("Italy", "it", "it", "it-IT"),
    ("Portugal", "pt-pt", "pt", "pt-PT"),
    ("Netherlands", "nl", "nl", "nl-NL"),
    ("Belgium", "be-en", "be", "en-BE"),
    ("Luxembourg", "lu-en", "lu", "en-LU"),
    ("Switzerland", "ch-en", "ch", "en-CH"),
    ("Austria", "at", "at", "de-AT"),
    ("Sweden", "se", "se", "sv-SE"),
    ("Norway", "no-en", "no", "en-NO"),
    ("Denmark", "dk", "dk", "da-DK"),
    ("Finland", "fi-en", "fi", "en-FI"),
    ("Iceland", "is-en", "is", "en-IS"),
    ("Poland", "pl", "pl", "pl-PL"),
    ("Czech Republic", "cz-en", "cz", "en-CZ"),
    ("Slovakia", "sk-en", "sk", "en-SK"),
    ("Hungary", "hu-en", "hu", "en-HU"),
    ("Romania", "ro-en", "ro", "en-RO"),
    ("Bulgaria", "bg-en", "bg", "en-BG"),
    ("Greece", "gr-en", "gr", "en-GR"),
    ("Cyprus", "cy-en", "cy", "en-CY"),
    ("Croatia", "hr-en", "hr", "en-HR"),
    ("Slovenia", "si-en", "si", "en-SI"),
    ("Serbia", "rs-en", "rs", "en-RS"),
    ("Bosnia and Herzegovina", "ba-en", "ba", "en-BA"),
    ("Montenegro", "me-en", "me", "en-ME"),
    ("North Macedonia", "mk-en", "mk", "en-MK"),
    ("Albania", "al-en", "al", "en-AL"),
    ("Malta", "mt-en", "mt", "en-MT"),
    ("Estonia", "ee-en", "ee", "en-EE"),
    ("Latvia", "lv-en", "lv", "en-LV"),
    ("Lithuania", "lt-en", "lt", "en-LT"),
    ("Ukraine", "ua-en", "ua", "en-UA"),
    ("Belarus", "by-en", "by", "en-BY"),
    ("Moldova", "md-en", "md", "en-MD"),
    ("Mexico", "mx-es", "mx", "es-MX"),
    ("Argentina", "ar-es", "ar", "es-AR"),
    ("Chile", "cl-es", "cl", "es-CL"),
    ("Colombia", "co-es", "co", "es-CO"),
    ("Peru", "pe-es", "pe", "es-PE"),
    ("Ecuador", "ec-es", "ec", "es-EC"),
    ("Uruguay", "uy-es", "uy", "es-UY"),
    ("Paraguay", "py-es", "py", "es-PY"),
    ("Bolivia", "bo-es", "bo", "es-BO"),
    ("Venezuela", "ve-es", "ve", "es-VE"),
    ("Costa Rica", "cr-es", "cr", "es-CR"),
    ("Panama", "pa-es", "pa", "es-PA"),
    ("Guatemala", "gt-es", "gt", "es-GT"),
    ("Honduras", "hn-es", "hn", "es-HN"),
    ("El Salvador", "sv-es", "sv", "es-SV"),
    ("Nicaragua", "ni-es", "ni", "es-NI"),
    ("Dominican Republic", "do-es", "do", "es-DO"),
    ("Puerto Rico", "pr-es", "pr", "es-PR"),
    ("Jamaica", "jm-en", "jm", "en-JM"),
    ("Trinidad and Tobago", "tt-en", "tt", "en-TT"),
    ("Bahamas", "bs-en", "bs", "en-BS"),
    ("Barbados", "bb-en", "bb", "en-BB"),
    ("Belize", "bz-en", "bz", "en-BZ"),
    ("Guyana", "gy-en", "gy", "en-GY"),
    ("Suriname", "sr-en", "sr", "en-SR"),
    ("Kenya", "ke-en", "ke", "en-KE"),
    ("Nigeria", "ng-en", "ng", "en-NG"),
    ("Ghana", "gh-en", "gh", "en-GH"),
    ("Uganda", "ug-en", "ug", "en-UG"),
    ("Tanzania", "tz-en", "tz", "en-TZ"),
    ("Zimbabwe", "zw-en", "zw", "en-ZW"),
    ("Zambia", "zm-en", "zm", "en-ZM"),
    ("Namibia", "na-en", "na", "en-NA"),
    ("Botswana", "bw-en", "bw", "en-BW"),
    ("Rwanda", "rw-en", "rw", "en-RW"),
    ("Ethiopia", "et-en", "et", "en-ET"),
    ("Senegal", "sn-en", "sn", "en-SN"),
    ("Mozambique", "mz-en", "mz", "en-MZ"),
    ("Angola", "ao-en", "ao", "en-AO"),
    ("Madagascar", "mg-en", "mg", "en-MG"),
    ("Mauritius", "mu-en", "mu", "en-MU"),
    ("Seychelles", "sc-en", "sc", "en-SC"),
]

regions = [
    {
        "name": name,
        "spotify_path": spotify_path,
        "apple_path": apple_path,
        "netflix_path": apple_path,
        "lang": lang,
    }
    for name, spotify_path, apple_path, lang in countries
]

PLAN_KEYWORDS = ["individual", "student", "duo", "family"]

PRICE_REGEX_BEFORE = re.compile(
    r"""
    (?P<currency>
        US\$|CA\$|AU\$|NZ\$|SG\$|R\$|₹|¥|€|£|\$|₺|₱|₩|Rp|RM|
        SAR|AED|EGP|LBP|CHF|SEK|NOK|DKK|PLN|MXN|ARS|CLP|COP|PEN|kr|₪
    )
    \s*
    (?P<amount>\d+(?:[.,]\d{1,2})?)
    """,
    re.VERBOSE | re.IGNORECASE,
)

PRICE_REGEX_AFTER = re.compile(
    r"""
    (?P<amount>\d+(?:[.,]\d{1,2})?)
    \s*
    (?P<currency>
        US\$|CA\$|AU\$|NZ\$|SG\$|R\$|₹|¥|€|£|\$|₺|₱|₩|Rp|RM|
        SAR|AED|EGP|LBP|CHF|SEK|NOK|DKK|PLN|MXN|ARS|CLP|COP|PEN|kr|₪
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

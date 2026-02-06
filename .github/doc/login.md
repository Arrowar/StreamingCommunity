# How to Extract Login Keys

Follow the instructions below to obtain the required keys for each streaming service and add them to your `config.json`.

## Crunchyroll: Get `etp_rt` and `device_id`

1. **Log in** to [Crunchyroll](https://www.crunchyroll.com/).
2. **Open Developer Tools** (<kbd>F12</kbd>).
3. **Get `etp_rt` and `device_id`:**
   - Go to the **Application** tab.
   - Find the `etp_rt` and `device_id` cookies under **Cookies** for the site (you can use the filter/search field and search for `etp_rt` or `device_id`).
   - **Copy** their values for `login.json`.
   - ![etp_rt location](./img/crunchyroll_etp_rt.png)


## Mediaset Infinity

1. **Log in** to [Mediaset](https://mediasetinfinity.mediaset.it/).
2. **Open Developer Tools** (<kbd>F12</kbd>).
3. **Get `beToken`:**
   - Go to the **Application** tab.
   - Filter for `acd` cookies under **Cookies** for the site (you can use the filter/search field and search for `beToken`).
   - **Copy** their values for `login.json`.
   - ![be Token](./img/mediasetinfinity_beToken.png)

## Discovery plus [EU]

1. **Log in** to [Discovery](https://play.discoveryplus.com/).
2. **Open Developer Tools** (<kbd>F12</kbd>).
3. **Get `st`:**
   - Go to the **Application** tab.
   - Find the `st` cookies under **Cookies** for the site (you can use the filter/search field and search for `st`).
   - **Copy** their values for `login.json`.
   - ![st location](./img/discoveryplus_eu_st.png)

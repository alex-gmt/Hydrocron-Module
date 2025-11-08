if __name__ == "__main__":
    import hydrocron.priorlake as pl
    # Site Data to Fetch
    sites = [
            ("FRUIT GROWERS RESERVOIR", 7720014282),
            ("JOHN MARTIN RESERVOIR", 7420077583),
            ("LAKE MALOYA", 7420077552),
            ("TELLER RESERVOIR", 7420078202)
             ]
    time_range = ("2023-03-20", "2025-11-05")
    fields = ['PLD_version', 'time_str', 'lake_id', 'lake_name', 'crid', 'wse']
    # Fetch and Process Data
    for site in sites:
        site_name, site_id = site
        print(f"Fetching Prior Lake data for {site_name} (ID: {site_id})...")
        response = pl.call_pl(site_id, time_range, fields)
        print(f"Response: {response.status_code}\n{response.url}\n")
        df = pl.read_pl(response)
        df[df['wse'] != -999999999999.0].to_csv(f"{site_name.replace(' ', '_')}_PriorLake_Data_VC.csv", index=False)

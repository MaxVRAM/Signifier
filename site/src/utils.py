

def split_config(main_config) -> tuple:
    """
    Construct a list of Prometheus metric objects for the push gateway
    """
    map_values = {'sources':{}, 'destinations':{}}
    mappings = {}
    comp_jobs = {}
    clip_categories = {}
    
    for module in list(main_config.keys()):
        if module == 'mapping':
            if 'rules' in main_config[module].keys():
                mappings = main_config[module].pop('rules')
        else:
            if 'sources' in main_config[module].keys():
                map_values['sources'].update({module:main_config[module].pop('sources')})
            if 'destinations' in main_config[module].keys():
                map_values['destinations'].update({module:main_config[module].pop('destinations')})
            if 'jobs' in main_config[module].keys():
                comp_jobs.update({module:main_config[module].pop('jobs')})
            if 'categories' in main_config[module].keys():
                clip_categories.update({module:main_config[module].pop('categories')})

    return (main_config, map_values, mappings, comp_jobs, clip_categories)
#!/usr/bin/env python3

"""
SublimeColorSchemeConverter

Converts sublime-color-scheme json files into tmTheme plist files.
"""

import os
import re
import json
import plistlib
import colorsys
import traceback
import collections
import sys

from lib import plistlib

re_var = re.compile("var\([^\)]+\)")
re_alpha = re.compile("alpha\(((0\.)?[0-9]+)\)")
re_hex = re.compile("(#[0-9,a-z,A-Z]{6})([0-9,a-z,A-Z]{2})?")
re_rgb = re.compile("rgb\((\d+),\s?(\d+),\s?(\d+)(,\s?(\d+\.?\d*))?\)")
re_hsl = re.compile("hsl\((\d+),\s?(\d+)%,\s?(\d+)%(,\s?(\d+\.?\d*))?\)")

def alpha_to_hex(a):
    return "{:02x}".format(int(255*float(a)))

def hexa_to_hex(hex, a):
    return hex[:7] + alpha_to_hex(a)

def rgb_to_hex(r, g, b, a=None):
    hexcode = "#{:02x}{:02x}{:02x}".format(r, g, b)
    if a:
        hexcode += alpha_to_hex(a)
    return hexcode

def get_alpha_adjuster(string, default=None):
    alpha = re_alpha.search(string)
    if alpha:
        return float(alpha.group(1))
    else:
        return default

def get_alpha_hex(hexcode):
    if len(hexcode) < 8:
        return None
    else:
        return int(hexcode[7:], 16)

def match_hex(string):
    match = re_hex.search(string)
    result = None
    if match:
        result = match.group(1)
        alpha = get_alpha_adjuster(string)
        if alpha:
            result += alpha_to_hex(alpha)
        elif match.group(2):
            result += match.group(2)
    return result

def match_rgb(string):
    match = re_rgb.search(string)
    result = None
    if match:
        r = int(match.group(1))
        g = int(match.group(2))
        b = int(match.group(3))
        a = get_alpha_adjuster(string, match.group(5))
        result = rgb_to_hex(r, g, b, a)
    return result

def match_hsl(string):
    match = re_hsl.search(string)
    result = None
    if match:
        h = int(match.group(1))/360
        s = int(match.group(2))/100
        l = int(match.group(3))/100
        a = get_alpha_adjuster(string, match.group(5))
        r, g, b = [255*int(v) for v in colorsys.hls_to_rgb(h, l, s)]
        result = rgb_to_hex(r, g, b, a)
    return result

def try_match_color(string):
    hexcode = match_hex(string)
    if not hexcode:
        hexcode = match_rgb(string)
    if not hexcode:
        hexcode = match_hsl(string)
    if hexcode:
        alpha = get_alpha_adjuster(string, get_alpha_hex(hexcode))
        if alpha:
            hexcode = hexa_to_hex(hexcode[:7], alpha)
    else:
        hexcode = string
    return hexcode

def convert_name(string):
    return re.sub(
        "_([a-z,A-Z,0-9])",
        lambda match: match.group(1).upper(),
        string
    )

def parse_color(key, variables):
    if variables and key in list(variables):
        return try_match_color(variables[key])
    else:
        var = re_var.search(key)
        if var:
            color = variables.get(var.group(), var.group())
            return try_match_color(key.replace(var.group(), color))
        else:
            return try_match_color(key)

def parse_settings(settings, variables):
    parsed = {}
    for key in list(settings):
        value = settings[key]
        parsed[convert_name(key)] = parse_color(value, variables)
    return parsed

def parse_scope(scope):
    parsed = convert_name(scope)
    parsed = re.sub("\s(-|\|)\s", ", ", parsed)
    parsed = re.sub("\s*(\(|\))\s*", " ", parsed)
    return parsed

def parse_rules(rules, variables):
    parsed = []
    for settings in rules:
        rule = {}
        name = settings.pop("name", None)
        if name:
            rule["name"] = name
        scope = settings.pop("scope", None)
        if scope:
            rule["scope"] = parse_scope(scope)
        rule["settings"] = parse_settings(settings, variables)
        parsed.append(rule)
    return parsed

def parse(source):
    name = source.get("name", "undefined")
    author = source.get("author", "undefined")
    variables = source.get("variables", None)
    globals_ = source["globals"]
    rules = source["rules"]

    if variables:
        for key in list(variables):
            variables["var({})".format(key)] = variables.pop(key)

    settings = parse_settings(globals_, variables)
    rules = parse_rules(rules, variables)
    return {
        "name": name,
        "author": author,
        "settings": [{"settings": settings}] + rules
    }

def convert(theme):
    dumps = plistlib.dumps(theme, sort_keys=False)
    return dumps.decode("UTF-8")

def read_source(src):
    with open(src) as sublime_color_scheme:
        return json.load(sublime_color_scheme)

def write_buffer(output, src):
    output_name = os.path.splitext(os.path.basename(src))[0] + ".tmTheme"
    with open(output_name, "w") as output_file:
        output_file.write(output)

def run(src):
    source = read_source(src)
    theme = parse(source)
    output = convert(theme)
    write_buffer(output, src)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("expected 2 args")
        sys.exit(1)

    run(sys.argv[1])

#!/usr/bin/env python
# generator.py
# simple C++ generator, originally targetted for Spidermonkey bindings
#
# Copyright (c) 2011 - Zynga Inc.

from clang import cindex
import sys
import ConfigParser
import yaml
import re
import os
import inspect
import traceback
import copy
from Cheetah.Template import Template

type_map = {
    cindex.TypeKind.VOID: "void",
    cindex.TypeKind.BOOL: "bool",
    cindex.TypeKind.CHAR_U: "unsigned char",
    cindex.TypeKind.UCHAR: "unsigned char",
    cindex.TypeKind.CHAR16: "char16_t",
    cindex.TypeKind.CHAR32: "char32_t",
    cindex.TypeKind.USHORT: "unsigned short",
    cindex.TypeKind.UINT: "unsigned int",
    cindex.TypeKind.ULONG: "unsigned long",
    cindex.TypeKind.ULONGLONG: "unsigned long long",
    cindex.TypeKind.CHAR_S: "char",
    cindex.TypeKind.SCHAR: "char",
    cindex.TypeKind.WCHAR: "wchar_t",
    cindex.TypeKind.SHORT: "short",
    cindex.TypeKind.INT: "int",
    cindex.TypeKind.LONG: "long",
    cindex.TypeKind.LONGLONG: "long long",
    cindex.TypeKind.FLOAT: "float",
    cindex.TypeKind.DOUBLE: "double",
    cindex.TypeKind.LONGDOUBLE: "long double",
    cindex.TypeKind.NULLPTR: "NULL",
    cindex.TypeKind.OBJCID: "id",
    cindex.TypeKind.OBJCCLASS: "class",
    cindex.TypeKind.OBJCSEL: "SEL",
    # cindex.TypeKind.ENUM        : "int"
}

INVALID_NATIVE_TYPE = "??"

default_arg_type_arr = [

    # An integer literal.
    cindex.CursorKind.INTEGER_LITERAL,

    # A floating point number literal.
    cindex.CursorKind.FLOATING_LITERAL,

    # An imaginary number literal.
    cindex.CursorKind.IMAGINARY_LITERAL,

    # A string literal.
    cindex.CursorKind.STRING_LITERAL,

    # A character literal.
    cindex.CursorKind.CHARACTER_LITERAL,

    # [C++ 2.13.5] C++ Boolean Literal.
    cindex.CursorKind.CXX_BOOL_LITERAL_EXPR,

    # [C++0x 2.14.7] C++ Pointer Literal.
    cindex.CursorKind.CXX_NULL_PTR_LITERAL_EXPR,

    cindex.CursorKind.GNU_NULL_EXPR,

    # An expression that refers to some value declaration, such as a function,
    # varible, or enumerator.
    cindex.CursorKind.DECL_REF_EXPR,

    cindex.CursorKind.CALL_EXPR
]

stl_type_map = {
    'std_function_args': 1000,
    'std::unordered_map': 2,
    'std::unordered_multimap': 2,
    'std::map': 2,
    'std::multimap': 2,
    'std::vector': 1,
    'std::list': 1,
    'std::forward_list': 1,
    'std::priority_queue': 1,
    'std::set': 1,
    'std::multiset': 1,
    'std::unordered_set': 1,
    'std::unordered_multiset': 1,
    'std::stack': 1,
    'std::queue': 1,
    'std::deque': 1,
    'std::array': 1,

    'unordered_map': 2,
    'unordered_multimap': 2,
    'map': 2,
    'multimap': 2,
    'vector': 1,
    'list': 1,
    'forward_list': 1,
    'priority_queue': 1,
    'set': 1,
    'multiset': 1,
    'unordered_set': 1,
    'unordered_multiset': 1,
    'stack': 1,
    'queue': 1,
    'deque': 1,
    'array': 1
}


def find_sub_string_count(s, start, end, substr):
    count = 0
    pos = s.find(substr, start, end)
    if pos != -1:
        next_count = find_sub_string_count(s, pos + 1, end, substr)
        count = next_count + 1
    return count


def split_container_name(name):
    name = name.strip()
    left = name.find('<')
    right = -1

    if left != -1:
        right = name.rfind('>')

    if left == -1 or right == -1:
        return [name]

    first = name[:left]
    results = [first]

    comma = name.find(',', left + 1, right)
    if comma == -1:
        results.append(name[left + 1:right].strip())
        name_len = len(name)
        if right < name_len - 1:
            last = name[right + 1:].strip()
            if last:
                results.append(last)
        return results

    left += 1
    while comma != -1:
        lt_count = find_sub_string_count(name, left, comma, '<')
        gt_count = find_sub_string_count(name, left, comma, '>')
        if lt_count == gt_count:
            results.append(name[left:comma].strip())
            left = comma + 1
        comma = name.find(',', comma + 1, right)

    if left < right:
        results.append(name[left:right].strip())
    name_len = len(name)
    if right < name_len - 1:
        results.append(name[right + 1:].strip())

    return results


def normalize_type_name_by_sections(sections):
    container_name = sections[0]
    suffix = ''

    index = len(sections) - 1
    while sections[index] == '*' or sections[index] == '&':
        suffix += sections[index]
        index -= 1

    name_for_search = container_name.replace('const ', '').replace('&', '').replace('*', '').strip()
    if name_for_search in stl_type_map:
        normalized_name = container_name + '<' + ', '.join(sections[1:1 + stl_type_map[name_for_search]]) + '>' + suffix
    else:
        normalized_name = container_name + '<' + ', '.join(sections[1:]) + '>'

    return normalized_name


def normalize_std_function_by_sections(sections):
    normalized_name = ''
    if sections[0] == 'std_function_args':
        normalized_name = '(' + ', '.join(sections[1:]) + ')'
    elif sections[0] == 'std::function' or sections[0] == 'function':
        normalized_name = 'std::function<' + sections[1] + ' ' + sections[2] + '>'
    else:
        assert (False)
    return normalized_name


def std_string_type_for(sections):
    if sections[1] == 'wchar_t':
        return "std::wstring"

    if sections[1] == 'char32_t':
        return "std::u32string"

    if sections[1] == 'char16_t':
        return "std::u16string"

    if sections[1] == 'char':
        return "std::string"

    return "??"


def normalize_type_str(s, depth=1):
    if s.find('std::function') == 0 or s.find('function') == 0:
        start = s.find('<')
        assert (start > 0)
        sections = [s[:start]]  # std::function
        start += 1
        ret_pos = s.find('(', start)
        sections.append(s[start:ret_pos].strip())  # return type
        end = s.find(')', ret_pos + 1)
        sections.append('std_function_args<' + s[ret_pos + 1:end].strip() + '>')
    else:
        sections = split_container_name(s)
    section_len = len(sections)
    if section_len == 1:
        return sections[0]

    # for section in sections:
    #     print('>' * depth + section)

    if sections[0] == 'const std::basic_string' or sections[0] == 'const basic_string':
        last_section = sections[len(sections) - 1]
        strtype = 'const {}'.format(std_string_type_for(sections))
        if last_section == '&' or last_section == '*' or last_section.startswith('::'):
            return strtype + last_section

        return strtype

    elif sections[0] == 'std::basic_string' or sections[0] == 'basic_string':
        last_section = sections[len(sections) - 1]
        strtype = std_string_type_for(sections)
        if last_section == '&' or last_section == '*' or last_section.startswith('::'):
            return strtype + last_section

        return strtype

    for i in range(1, section_len):
        sections[i] = normalize_type_str(sections[i], depth + 1)

    if sections[0] == 'std::function' or sections[0] == 'function' or sections[0] == 'std_function_args':
        normalized_name = normalize_std_function_by_sections(sections)
    else:
        normalized_name = normalize_type_name_by_sections(sections)
    return normalized_name


class BaseEnumeration(object):
    """
    Common base class for named enumerations held in sync with Index.h values.

    Subclasses must define their own _kinds and _name_map members, as:
    _kinds = []
    _name_map = None
    These values hold the per-subclass instances and value-to-name mappings,
    respectively.

    """

    def __init__(self, value):
        if value >= len(self.__class__._kinds):
            self.__class__._kinds += [None] * (value - len(self.__class__._kinds) + 1)
        if self.__class__._kinds[value] is not None:
            raise ValueError('{0} value {1} already loaded'.format(
                str(self.__class__), value))
        self.value = value
        self.__class__._kinds[value] = self
        self.__class__._name_map = None

    def from_param(self):
        return self.value

    @property
    def name(self):
        """Get the enumeration name of this cursor kind."""
        if self._name_map is None:
            self._name_map = {}
            for key, value in self.__class__.__dict__.items():
                if isinstance(value, self.__class__):
                    self._name_map[value] = key
        return self._name_map[self]

    @classmethod
    def from_id(cls, id):
        if id >= len(cls._kinds) or cls._kinds[id] is None:
            raise ValueError('Unknown template argument kind %d' % id)
        return cls._kinds[id]

    def __repr__(self):
        return '%s.%s' % (self.__class__, self.name,)


### Availability Kinds ###

class AvailabilityKind(BaseEnumeration):
    """
    Describes the availability of an entity.
    """

    # The unique kind objects, indexed by id.
    _kinds = []
    _name_map = None

    def __repr__(self):
        return 'AvailabilityKind.%s' % (self.name,)


AvailabilityKind.AVAILABLE = AvailabilityKind(0)
AvailabilityKind.DEPRECATED = AvailabilityKind(1)
AvailabilityKind.NOT_AVAILABLE = AvailabilityKind(2)
AvailabilityKind.NOT_ACCESSIBLE = AvailabilityKind(3)


def get_availability(cursor):
    """
    Retrieves the availability of the entity pointed at by the cursor.
    """
    if not hasattr(cursor, '_availability'):
        cursor._availability = cindex.conf.lib.clang_getCursorAvailability(cursor)

    return AvailabilityKind.from_id(cursor._availability)


def native_name_from_type(ntype, underlying=False):
    kind = ntype.kind  # get_canonical().kind
    const = ""  # "const " if ntype.is_const_qualified() else ""
    if not underlying and kind == cindex.TypeKind.ENUM:
        decl = ntype.get_declaration()
        return get_namespaced_name(decl)
    elif kind in type_map:
        return const + type_map[kind]
    elif kind == cindex.TypeKind.RECORD:
        # might be an std::string
        decl = ntype.get_declaration()
        parent = decl.semantic_parent
        cdecl = ntype.get_canonical().get_declaration()
        cparent = cdecl.semantic_parent
        if decl.spelling == "string" and parent and parent.spelling == "std":
            return "std::string"
        elif cdecl.spelling == "function" and cparent and cparent.spelling == "std":
            return "std::function"
        else:
            # print >> sys.stderr, "probably a function pointer: " + str(decl.spelling)
            return const + decl.spelling
    else:
        # name = ntype.get_declaration().spelling
        # print >> sys.stderr, "Unknown type: " + str(kind) + " " + str(name)
        return INVALID_NATIVE_TYPE
        # pdb.set_trace()


def build_namespace(cursor, namespaces=[]):
    '''
    build the full namespace for a specific cursor
    '''
    if cursor:
        parent = cursor.semantic_parent
        if parent:
            if parent.kind == cindex.CursorKind.NAMESPACE or parent.kind == cindex.CursorKind.CLASS_DECL or \
                    parent.kind == cindex.CursorKind.STRUCT_DECL:
                namespaces.append(parent.displayname)
                build_namespace(parent, namespaces)

    return namespaces


def get_namespaced_name(declaration_cursor):
    ns_list = build_namespace(declaration_cursor, [])
    ns_list.reverse()
    ns = "::".join(ns_list)
    display_name = declaration_cursor.displayname.replace("::__ndk1", "")
    display_name = display_name.replace("::__1", "")
    if len(ns) > 0:
        ns = ns.replace("::__ndk1", "")
        ns = ns.replace("::__1", "")
        return ns + "::" + display_name
    return display_name


def generate_namespace_list(cursor, namespaces=[]):
    '''
    build the full namespace for a specific cursor
    '''
    if cursor:
        parent = cursor.semantic_parent
        if parent:
            if parent.kind == cindex.CursorKind.NAMESPACE or \
                    parent.kind == cindex.CursorKind.CLASS_DECL or parent.kind == cindex.CursorKind.STRUCT_DECL:
                if parent.kind == cindex.CursorKind.NAMESPACE:
                    namespaces.append(parent.displayname)
                generate_namespace_list(parent, namespaces)
    return namespaces


def get_namespace_name(declaration_cursor):
    ns_list = generate_namespace_list(declaration_cursor, [])
    ns_list.reverse()
    ns = "::".join(ns_list)

    if len(ns) > 0:
        ns = ns.replace("::__ndk1", "")
        ns = ns.replace("::__1", "")
        return ns + "::"

    return ""


class NativeType(object):
    def __init__(self):
        self.is_object = False
        self.is_function = False
        self.is_enum = False
        self.is_numeric = False
        self.not_supported = False
        self.param_types = []
        self.ret_type = None
        self.namespaced_name = ""  # with namespace and class name
        self.namespace_name = ""  # only contains namespace
        self.name = ""
        self.whole_name = None
        self.is_const = False
        self.is_pointer = False
        self.should_cast = False
        self.canonical_type = None

    def same_as(self, other, check_const=True):
        if self == other:
            return True

        if check_const and self.is_const != other.is_const:
            return False

        if self.is_pointer != other.is_pointer:
            return False

        if (self.ret_type is None) != (other.ret_type is None):
            return False

        param_count = len(self.param_types)
        if param_count != len(other.param_types):
            return False

        if self.namespaced_name != other.namespaced_name and \
                (self.canonical_type is None or self.canonical_type.namespaced_name != other.namespaced_name) and \
                (other.canonical_type is None or self.namespaced_name != other.canonical_type.namespaced_name):
            return False

        if self.ret_type is not None and not self.ret_type.same_as(other.ret_type):
            return False

        index = 0
        while index < param_count:
            if not self.param_types[index].same_as(other.param_types[index]):
                return False
            index += 1

        return True

    @staticmethod
    def from_type(ntype):
        if ntype.kind == cindex.TypeKind.POINTER:
            nt = NativeType.from_type(ntype.get_pointee())

            if nt.canonical_type is not None:
                nt.canonical_type.name += "*"
                nt.canonical_type.namespaced_name += "*"
                nt.canonical_type.whole_name += "*"

            nt.name += "*"
            nt.namespaced_name += "*"
            nt.whole_name = nt.namespaced_name
            nt.is_enum = False
            nt.is_const = ntype.get_pointee().is_const_qualified()
            nt.is_pointer = True
            if nt.is_const:
                nt.whole_name = "const " + nt.whole_name
        elif ntype.kind == cindex.TypeKind.LVALUEREFERENCE:
            nt = NativeType.from_type(ntype.get_pointee())
            nt.is_const = ntype.get_pointee().is_const_qualified()
            nt.whole_name = nt.namespaced_name + "&"

            if nt.is_const:
                nt.whole_name = "const " + nt.whole_name

            if nt.canonical_type is not None:
                nt.canonical_type.whole_name += "&"
        else:
            nt = NativeType()
            decl = ntype.get_declaration()

            nt.namespaced_name = get_namespaced_name(decl).replace('::__ndk1', '')
            nt.namespaced_name = nt.namespaced_name.replace('::__1', '')

            if ((decl.kind == cindex.CursorKind.CLASS_DECL
                or decl.kind == cindex.CursorKind.STRUCT_DECL)
                    and not nt.namespaced_name.startswith('std::function')
                    and not nt.namespaced_name.startswith('std::string')
                    and not nt.namespaced_name.startswith('std::basic_string')):
                nt.is_object = True
                nt.namespaced_name = normalize_type_str(nt.namespaced_name)
                nt.namespace_name = get_namespace_name(decl)
                nt.name = nt.namespaced_name[len(nt.namespace_name):]
                nt.whole_name = nt.namespaced_name
            else:
                if decl.kind == cindex.CursorKind.NO_DECL_FOUND:
                    nt.name = native_name_from_type(ntype)
                else:
                    nt.name = decl.spelling
                nt.namespace_name = get_namespace_name(decl)

                if len(nt.namespaced_name) > 0:
                    nt.namespaced_name = normalize_type_str(nt.namespaced_name)
                    if '::' not in nt.name:
                        nt.name = nt.namespaced_name[len(nt.namespace_name):]

                if nt.namespaced_name.startswith("std::function"):
                    nt.name = "std::function"

                if len(nt.namespaced_name) == 0 or nt.namespaced_name.find("::") == -1:
                    nt.namespaced_name = nt.name

                nt.whole_name = nt.namespaced_name
                nt.is_const = ntype.is_const_qualified()
                if nt.is_const:
                    nt.whole_name = "const " + nt.whole_name

                canonical = ntype.get_canonical()
                # Check whether it's a std::function typedef
                cdecl = canonical.get_declaration()
                if cdecl.spelling is not None and 0 == cmp(cdecl.spelling, "function"):
                    nt.name = "std::function"

                nt.is_enum = canonical.kind == cindex.TypeKind.ENUM

                if (nt.name != INVALID_NATIVE_TYPE
                        and canonical.kind != ntype.kind
                        and nt.namespaced_name != "std::string"
                        and nt.name != "std::function"):
                    canonical = NativeType.from_type(canonical)
                    if canonical.name:
                        if '<' in canonical.name:
                            nt.canonical_type = canonical
                        else:
                            temp = nt
                            nt = canonical
                            nt.canonical_type = temp

                if nt.name == "std::function":
                    nt.is_object = False
                    lambda_display_name = get_namespaced_name(cdecl)
                    lambda_display_name = lambda_display_name.replace("::__ndk1", "")
                    lambda_display_name = lambda_display_name.replace("::__1", "")
                    lambda_display_name = normalize_type_str(lambda_display_name)
                    if nt.namespaced_name.startswith('std::function'):
                        nt.namespaced_name = lambda_display_name
                    r = re.compile(r'function<([^\s]+).*\((.*)\)>').search(
                        lambda_display_name)
                    (ret_type, params) = r.groups()
                    params = filter(None, params.split(", "))

                    nt.is_function = True
                    nt.ret_type = NativeType.from_string(ret_type)
                    nt.param_types = [NativeType.from_string(string) for string in params]

        nt.finish_init()
        return nt

    def finish_init(self):
        # mark argument as not supported
        if not self.not_supported:
            if self.name == INVALID_NATIVE_TYPE:
                self.not_supported = True

        self.is_numeric = False
        if not self.is_pointer:
            name = self.name.split(' ')
            if name:
                name = name[-1]
                if re.match("^(unsigned|char|short|ushort|int|uint|double|float|long|size_t|ssize_t|int32_t|uint32_t|"
                            "intptr_t|uintptr_t|qintptr|quintptr|qlonglong|qulonglong|int8_t|uint8_t|int16_t|uint16_t|"
                            "int64_t|uint64_t|qreal|qint8|qint16|qint32|qint64|quint8|quint16|quint32|quint64|qsizetype)$",
                            name) is not None:
                    self.is_numeric = True

        self.not_supported = self.not_supported or ('?' in self.namespaced_name)
        self.is_object = not self.is_pointer and not self.is_numeric and not self.not_supported and not self.is_enum

    @staticmethod
    def from_string(displayname):
        nt = NativeType()
        displayname = displayname.strip()
        if displayname.startswith('const '):
            nt.is_const = True
            displayname = displayname[6:]
        displayname = displayname.strip()
        amp_count = 0
        while displayname.endswith('&'):
            displayname = displayname[:-1].strip()
            amp_count += 1

        stars_count = 0
        while displayname.endswith('*'):
            nt.is_pointer = True
            displayname = displayname[:-1].strip()
            stars_count += 1

        if stars_count > 0:
            displayname += '*' * stars_count
        nt.whole_name = 'const ' + displayname if nt.is_const else displayname
        nt.whole_name += '&' * amp_count

        split_name = displayname.split("::")
        nt.namespace_name = '::'.join(split_name[:-1])
        if nt.namespace_name:
            nt.namespace_name += '::'
        nt.namespaced_name = displayname.replace('.', '::')
        nt.name = nt.namespaced_name.split("::")[-1]

        nt.finish_init()
        return nt

    @property
    def lambda_parameters(self):
        params = ["%s larg%d" % (str(nt), i) for i, nt in enumerate(self.param_types)]
        return ", ".join(params)

    @staticmethod
    def dict_has_key_re(dict, real_key_list):
        for real_key in real_key_list:
            for (k, v) in dict.items():
                if k.startswith('@'):
                    k = k[1:]
                    match = re.match("^" + k + "$", real_key)
                    if match:
                        return True
                else:
                    if k == real_key:
                        return True
        return False

    @staticmethod
    def dict_get_value_re(dict, real_key_list):
        for real_key in real_key_list:
            for (k, v) in dict.items():
                if k.startswith('@'):
                    k = k[1:]
                    match = re.match("^" + k + "$", real_key)
                    if match:
                        return v
                else:
                    if k == real_key:
                        return v
        return None

    @staticmethod
    def dict_replace_value_re(dict, real_key_list):
        for real_key in real_key_list:
            for (k, v) in dict.items():
                if k.startswith('@'):
                    k = k[1:]
                    match = re.match('.*' + k, real_key)
                    if match:
                        return re.sub(k, v, real_key)
                else:
                    if k == real_key:
                        return v
        return None

    def from_native(self, convert_opts):
        assert (convert_opts.has_key('generator'))
        generator = convert_opts['generator']
        this_method = convert_opts.get('this_method', None)
        keys = []

        if self.canonical_type is not None:
            keys.append(self.canonical_type.namespaced_name)
        keys.append(self.namespaced_name)

        from_native_dict = generator.config['conversions']['from_native']

        if self.is_object:
            if not NativeType.dict_has_key_re(from_native_dict, keys):
                keys.append("object")
        elif self.is_enum:
            keys.append('enum')
            keys.append("int")

        result = None
        tpl = NativeType.dict_get_value_re(from_native_dict, keys)
        if tpl:
            tpl = Template(tpl, searchList=[convert_opts])
            result = str(tpl).rstrip()

        if result is None and 'default' in convert_opts:
            result = convert_opts['default']

        if result is None:
            return "#pragma warning NO CONVERSION FROM NATIVE FOR " + self.name

        if (this_method is not None
                and this_method.native_call_return is not None):
            return this_method.native_call_return.format(result)

        if not self.is_const and self.whole_name.endswith('&'):
            return '&' + result

        if self.should_cast:
            if self.is_object:
                fmt = "{}({})"
            elif self.is_pointer and self.is_const:
                fmt = "static_cast<const {}>({})"
            else:
                fmt = "static_cast<{}>({})"
            result = fmt.format(self.namespaced_name, result)

        return result

    def to_native(self, convert_opts):
        assert ('generator' in convert_opts)
        generator = convert_opts['generator']
        keys = []

        if self.canonical_type is not None:
            keys.append(self.canonical_type.namespaced_name)
        keys.append(self.namespaced_name)

        to_native_dict = generator.config['conversions']['to_native']
        if self.is_object:
            if not NativeType.dict_has_key_re(to_native_dict, keys):
                keys.append("object")
        elif self.is_enum:
            keys.append("enum")
            keys.append("int")

        if self.is_function:
            tpl = Template(file=os.path.join(generator.target, "templates", "lambda.c"),
                           searchList=[convert_opts, self])
            indent = convert_opts.get('level', 0) * "\t"
            return str(tpl).replace("\n", "\n" + indent)

        result = None
        tpl = NativeType.dict_get_value_re(to_native_dict, keys)
        if tpl:
            tpl = Template(tpl, searchList=[convert_opts])
            result = str(tpl).rstrip()

        if result is None and 'default' in convert_opts:
            result = convert_opts['default']

        if result is not None:
            if not self.is_const and self.whole_name.endswith('&'):
                return '*' + result
            return result

        return "#pragma warning NO CONVERSION TO NATIVE FOR " + self.name + "\n" + convert_opts[
            'level'] * "\t" + "ok = false"

    def to_string(self, generator):
        name = self.namespaced_name
        keys = [name]
        conversions = generator.config['conversions']

        to_native_dict = conversions['to_native']
        from_native_dict = conversions['from_native']
        use_typedef = False

        typedef_name = self.canonical_type.name if self.canonical_type is not None else None

        if typedef_name is not None:
            if NativeType.dict_has_key_re(to_native_dict, [
                typedef_name]) or NativeType.dict_has_key_re(
                    from_native_dict, [typedef_name]):
                use_typedef = True

        if use_typedef:
            name = self.canonical_type.namespaced_name
            keys = [name] + keys

        if 'native_types' in conversions:
            native_types_dict = conversions['native_types']
            if self.is_enum:
                keys.append('enum')
            if self.is_function:
                keys.append('std::function')
            to_replace = NativeType.dict_get_value_re(native_types_dict, keys)
            if to_replace:
                if not self.is_const and self.whole_name.endswith('&'):
                    to_replace += '*'
                return to_replace

        result = self.with_qualifier(name)
        if not self.is_const and self.whole_name.endswith('&'):
            result += '*'

        return result

    def with_qualifier(self, name):
        if self.is_pointer and self.is_const:
            name = 'const ' + name
        return name

    def get_whole_name(self, generator):
        conversions = generator.config['conversions']

        to_native_dict = conversions['to_native']
        from_native_dict = conversions['from_native']

        name = self.namespaced_name
        keys = [name]
        typedef_name = self.canonical_type.name if self.canonical_type is not None else None

        use_typedef = False
        if typedef_name is not None:
            if NativeType.dict_has_key_re(to_native_dict, [
                typedef_name]) or NativeType.dict_has_key_re(
                    from_native_dict, [typedef_name]):
                use_typedef = True

        if use_typedef:
            name = self.canonical_type.namespaced_name
            keys = [name] + keys

        to_replace = None
        if 'native_types' in conversions:
            native_types_dict = conversions['native_types']

            if self.is_enum:
                keys.append('enum')
            if self.is_function:
                keys.append('std::function')
            to_replace = NativeType.dict_replace_value_re(native_types_dict, keys)

        if to_replace:
            if self.is_pointer and not to_replace.endswith('*'):
                if self.is_const:
                    name = self.with_qualifier(to_replace) + '&'
                else:
                    name = to_replace + '*'
            else:
                name = to_replace
                if not self.is_function or generator.script_type != "qtscript":
                    if self.whole_name.endswith('&'):
                        name += '&'

                    if self.is_const:
                        name = 'const ' + name
        else:
            name = self.canonical_type.whole_name if use_typedef else self.whole_name

        if name.endswith('&') and not name.startswith('const '):
            name = name[:-1] + '*'

        return name

    def object_can_convert(self, generator, is_to_native=True):
        if self.is_object:
            keys = []
            if self.canonical_type != None:
                keys.append(self.canonical_type.name)
            keys.append(self.name)
            if is_to_native:
                to_native_dict = generator.config['conversions']['to_native']
                if NativeType.dict_has_key_re(to_native_dict, keys):
                    return True
            else:
                from_native_dict = generator.config['conversions']['from_native']
                if NativeType.dict_has_key_re(from_native_dict, keys):
                    return True

        return False

    def __str__(self):
        return self.canonical_type.whole_name if None != self.canonical_type else self.whole_name


class NativeField(object):
    def __init__(self, cursor):
        cursor = cursor.canonical
        self.cursor = cursor
        self.name = cursor.displayname
        self.kind = cursor.type.kind
        self.location = cursor.location

        pretty_name = to_property_name('m_', self.name)
        if pretty_name is None and len(self.name) >= 2:
            second_letter = self.name[1:2]
            if second_letter.upper() == second_letter:
                pretty_name = to_property_name('m', self.name)

        if pretty_name is None:
            pretty_name = to_property_name('_', self.name)

        if pretty_name is None:
            pretty_name = self.name

        self.pretty_name = pretty_name
        self.signature_name = self.name
        self.ntype = NativeType.from_type(cursor.type)

    @staticmethod
    def can_parse(ntype):
        native_type = NativeType.from_type(ntype)
        if ntype.kind == cindex.TypeKind.UNEXPOSED and native_type.name != "std::string":
            return False
        return True

    def generate_code(self, current_class=None, generator=None):
        gen = current_class.generator if current_class else generator
        config = gen.config

        if config['definitions'].has_key('public_field'):
            tpl = Template(config['definitions']['public_field'],
                           searchList=[current_class, self])
            self.signature_name = str(tpl)

        tpl = Template(file=os.path.join(gen.target, "templates", "public_field.h"),
                       searchList=[current_class, self])
        gen.head_file.write(str(tpl))

        tpl = Template(file=os.path.join(gen.target, "templates", "public_field.c"),
                       searchList=[current_class, self])
        gen.impl_file.write(str(tpl))


# return True if found default argument.
def iterate_param_node(param_node, depth=1):
    for node in param_node.get_children():
        # print(">"*depth+" "+str(node.kind))
        if node.kind in default_arg_type_arr:
            return True

        if iterate_param_node(node, depth + 1):
            return True

    return False


def convert_nt_with_class(nt, cls):
    if nt.namespaced_name.startswith('~CurrentClassObject~'):
        s = cls.namespaced_class_name
        if nt.is_pointer:
            s += '*'
        if nt.is_const:
            s = 'const ' + s
        if nt.whole_name.endswith('&'):
            s += '&'
        return NativeType.from_string(s)

    return nt


def has_copy_argument(min_args, max_args, arguments, cls):
    return min_args <= 1 <= max_args and (arguments[0].whole_name == cls.namespaced_class_name or \
                                          arguments[0].whole_name == 'const ' + cls.namespaced_class_name + '&')


class NativeFunction(object):
    def __init__(self, cursor, is_constructor, cls):
        self.cursor = cursor
        self.func_name = cursor.spelling
        self.registration_name = self.func_name
        self.not_supported = False

        arguments = []

        for arg in cursor.type.argument_types():
            arguments.append(NativeType.from_type(arg))

        found_default_arg = False
        default_arg_index = -1
        for arg_node in self.cursor.get_children():
            if arg_node.kind == cindex.CursorKind.PARM_DECL:
                default_arg_index += 1
                if iterate_param_node(arg_node):
                    found_default_arg = True
                    break

        max_args = len(arguments)
        min_args = default_arg_index if found_default_arg else max_args

        ret_type = NativeType.from_type(cursor.result_type)
        reg_params = None
        should_rename = False

        obj_arr = cls.generator.should_rename_function(cls, self.func_name)
        if obj_arr:
            for obj in obj_arr:
                rename_args = obj['args']
                rename_ret = obj['ret_type']
                should_rename = rename_args is None
                if not should_rename and len(rename_args) == max_args and \
                        (rename_ret is None or convert_nt_with_class(rename_ret, cls).same_as(ret_type)):
                    should_rename = True
                    idx = 0
                    while idx < max_args:
                        arg = rename_args[idx]
                        if arg is not None and not convert_nt_with_class(arg, cls).same_as(arguments[idx]):
                            should_rename = False
                            break
                        idx += 1
                if should_rename:
                    reg_params = obj['to']
                    self.registration_name = reg_params['name']
                    break

        self.signature_name = self.registration_name
        self.arguments = []
        self.argument_names = []
        self.static = cursor.kind == cindex.CursorKind.CXX_METHOD and cursor.is_static_method()
        self.is_const = cursor.kind == cindex.CursorKind.CXX_METHOD and cursor.is_const_method()
        self.implementations = []
        self.is_overloaded = False
        self.is_constructor = is_constructor
        self.is_virtual = cursor.kind == cindex.CursorKind.CXX_METHOD and cursor.is_virtual_method()
        self.is_pure_virtual = self.is_virtual and cursor.is_pure_virtual_method()
        self.is_property_method = False
        self.comment = self.get_comment(cursor.raw_comment)
        self.is_override = False
        self.max_args = 0
        self.min_args = 0

        self.real_min_args = min_args
        self.is_copy_operator = (
                not self.static
                and (is_constructor or self.func_name == 'operator=')
                and has_copy_argument(min_args, max_args, arguments, cls))

        if self.registration_name == '0':
            self.registration_name = self.func_name
            self.not_supported = True

        argument_names = []
        arg_idx = 0
        for arg in cursor.get_arguments():
            arg_name = arg.spelling
            if arg_name == "":
                while True:
                    arg_name = "arg" + str(arg_idx)
                    arg_idx += 1
                    if arg_name not in argument_names:
                        break
            argument_names.append(arg_name)

        assert max_args == len(argument_names)
        native_call_args = None
        native_call_return = None

        if should_rename:
            reg_ret = reg_params['ret_type']

            if reg_ret is not None:
                current_class_rt = convert_nt_with_class(reg_ret, cls)
                if current_class_rt.same_as(reg_ret):
                    reg_ret = NativeType.from_string(reg_ret.whole_name)
                else:
                    self.is_virtual = False
                    reg_ret = current_class_rt

                reg_ret.should_cast = reg_ret.namespaced_name != 'void' and not reg_ret.same_as(ret_type)
                ret_type = reg_ret

            args = reg_params['args']
            native_call_args = reg_params['native_args']
            if args is not None and native_call_args is not None:
                new_names = []
                new_arg_count = len(args)
                new_args = []
                idx = 0
                arg_idx = 0
                while idx < new_arg_count:
                    new_names.append('arg' + str(idx))
                    arg = args[idx]
                    if arg is None:
                        if arg_idx < max_args:
                            arg = arguments[arg_idx]
                            arg_idx += 1
                    elif arg.namespaced_name.isdigit():
                        arg = arguments[int(arg.namespaced_name)]
                    new_args.append(arg)
                    idx += 1

                native_call_args_len = len(native_call_args)
                if ret_type != "void":
                    if native_call_args_len > max_args:
                        native_call_return = ','.join(
                            native_call_args[max_args:])
                        native_call_args = native_call_args[:max_args]
                        native_call_args_len = max_args
                if native_call_args_len != max_args:
                    raise Exception('native argument count mismatch')
                arguments = new_args
                argument_names = new_names
                max_args = new_arg_count
                min_args = new_arg_count

        self.native_call_args = native_call_args
        self.native_call_return = native_call_return
        self.arguments = arguments
        self.argument_names = argument_names
        self.ret_type = ret_type
        if ret_type.not_supported:
            self.not_supported = True

        if not self.not_supported:
            for arg in arguments:
                # mark the function as not supported if at least one argument is not supported
                if arg.not_supported:
                    self.not_supported = True
                    break

        self.max_args = max_args
        self.min_args = min_args

        self.is_override = self._is_override(cls)
        if self.is_override:
            self.is_virtual = True

    def get_decl_arg_list(self, generator, count):
        if count > len(self.arguments):
            raise Exception('bad arg count')
        arg_idx = 0
        result = []
        while arg_idx < count:
            arg = self.arguments[arg_idx]
            arg_name = self.argument_names[arg_idx]
            result.append(arg.get_whole_name(generator) + " " + arg_name)
            arg_idx += 1

        return result

    def get_call_arg_list(self, generator, count):
        if count > len(self.arguments):
            raise Exception('bad arg count')
        result = []
        index = 0
        while index < count:
            arg = self.arguments[index]
            arg_name = self.argument_names[index]
            arg_native = arg.to_native({
                "generator": generator,
                "arg": arg,
                "in_value": arg_name,
                "default": arg_name
            })
            result.append(arg_native)
            index += 1
        return result

    def get_native_call_args_with_list(self, arg_list):
        if self.native_call_args is None:
            return arg_list

        result = []
        arg_count = len(arg_list)

        for arg in self.native_call_args:
            fmt_args = []
            i = 0
            new_i = 0
            new_arg = arg
            while i < arg_count:
                fmt = '{' + str(i) + '}'
                if fmt in arg:
                    fmt_args.append(arg_list[i])
                    new_arg = new_arg.replace(fmt, '{' + str(new_i) + '}')
                    new_i += 1
                i += 1

            result.append(new_arg.format(*fmt_args))

        return result

    def get_native_call_args(self, generator, count):
        return self.get_native_call_args_with_list(self.get_call_arg_list(generator, count))

    def check_is_override(self, other):
        return other.is_virtual and self.same_as(other)

    def _is_override(self, cls):
        if cls is None:
            return False

        if self.is_pure_virtual:
            return False

        cls = cls.base_parent
        while cls is not None:
            if self.registration_name in cls.all_methods:
                parent_m = cls.all_methods[self.registration_name]

                if isinstance(parent_m, NativeOverloadedFunction):
                    for parent_mimpl in parent_m.implementations:
                        if self.check_is_override(parent_mimpl):
                            return True
                elif self.check_is_override(parent_m):
                    return True

            cls = cls.base_parent

        return False

    def same_as(self, other, check_const=True):
        if self == other:
            return True

        if check_const and self.is_const != other.is_const:
            return False

        if self.is_constructor != other.is_constructor:
            return False

        if self.max_args != other.max_args:
            return False

        if self.func_name != other.func_name:
            return False

        if not self.ret_type.same_as(other.ret_type, check_const):
            return False

        index = 0
        while index < self.max_args:
            if not self.arguments[index].same_as(other.arguments[index]):
                return False
            index += 1

        return True

    def get_comment(self, comment):
        replaceStr = comment

        if comment is None:
            return ""

        regular_replace_list = [
            ("(\s)*//!", ""),
            ("(\s)*//", ""),
            ("(\s)*/\*\*", ""),
            ("(\s)*/\*", ""),
            ("\*/", ""),
            ("\r\n", "\n"),
            ("\n(\s)*\*", "\n"),
            ("\n(\s)*@", "\n"),
            ("\n(\s)*", "\n"),
            ("\n(\s)*\n", "\n"),
            ("^(\s)*\n", ""),
            ("\n(\s)*$", ""),
            ("\n", "<br>\n"),
            ("\n", "\n-- ")
        ]

        for item in regular_replace_list:
            replaceStr = re.sub(item[0], item[1], replaceStr)

        return replaceStr

    def generate_code(self, current_class=None, generator=None):
        gen = current_class.generator if current_class else generator
        config = gen.config

        if self.is_constructor:
            tpl = Template(file=os.path.join(gen.target, "templates", "constructor.h"),
                           searchList=[current_class, self, {"this_method": self}])
        elif self.static:
            tpl = Template(file=os.path.join(gen.target, "templates", "sfunction.h"),
                           searchList=[current_class, self, {"this_method": self}])
        else:
            tpl = Template(file=os.path.join(gen.target, "templates", "ifunction.h"),
                           searchList=[current_class, self, {"this_method": self}])

        gen.head_file.write(str(tpl))

        if self.static:
            if config['definitions'].has_key('sfunction'):
                tpl = Template(config['definitions']['sfunction'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "sfunction.c"),
                           searchList=[current_class, self, {"this_method": self}])
        elif self.is_constructor:
            if config['definitions'].has_key('constructor'):
                tpl = Template(config['definitions']['constructor'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "constructor.c"),
                           searchList=[current_class, self, {"this_method": self}])
        else:
            if config['definitions'].has_key('ifunction'):
                tpl = Template(config['definitions']['ifunction'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "ifunction.c"),
                           searchList=[current_class, self, {"this_method": self}])

        gen.impl_file.write(str(tpl))


class NativeOverloadedFunction(object):
    def __init__(self, func_array):
        self.implementations = func_array
        self.func_name = func_array[0].func_name
        self.registration_name = func_array[0].registration_name
        self.signature_name = self.func_name
        self.min_args = 100
        self.max_args = 0
        self.is_constructor = False
        self.is_overloaded = True
        for m in func_array:
            self.min_args = min(self.min_args, m.min_args)
            self.max_args = max(self.max_args, m.max_args)

        self.comment = self.get_comment(func_array[0].cursor.raw_comment)

    def get_comment(self, comment):
        replaceStr = comment

        if comment is None:
            return ""

        regular_replace_list = [
            ("(\s)*//!", ""),
            ("(\s)*//", ""),
            ("(\s)*/\*\*", ""),
            ("(\s)*/\*", ""),
            ("\*/", ""),
            ("\r\n", "\n"),
            ("\n(\s)*\*", "\n"),
            ("\n(\s)*@", "\n"),
            ("\n(\s)*", "\n"),
            ("\n(\s)*\n", "\n"),
            ("^(\s)*\n", ""),
            ("\n(\s)*$", ""),
            ("\n", "<br>\n"),
            ("\n", "\n-- ")
        ]

        for item in regular_replace_list:
            replaceStr = re.sub(item[0], item[1], replaceStr)

        return replaceStr

    def append(self, func):
        self.min_args = min(self.min_args, func.min_args)
        self.max_args = max(self.max_args, func.max_args)
        self.implementations.append(func)

    def generate_code(self, current_class=None):
        gen = current_class.generator
        config = gen.config

        static_count = 0
        for impl in self.implementations:
            if impl.static:
                static_count += 1

        if self.is_constructor:
            tpl = Template(file=os.path.join(gen.target, "templates", "constructor.h"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.head_file.write(str(tpl))

            if config['definitions'].has_key('constructor'):
                tpl = Template(config['definitions']['constructor'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "constructor.c"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.impl_file.write(str(tpl))
            return

        if static_count > 0:
            tpl = Template(file=os.path.join(gen.target, "templates", "sfunction_overloaded.h"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.head_file.write(str(tpl))

            if config['definitions'].has_key('sfunction'):
                tpl = Template(config['definitions']['sfunction'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "sfunction_overloaded.c"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.impl_file.write(str(tpl))

        if static_count < len(self.implementations):
            tpl = Template(file=os.path.join(gen.target, "templates", "ifunction_overloaded.h"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.head_file.write(str(tpl))

            if config['definitions'].has_key('ifunction'):
                tpl = Template(config['definitions']['ifunction'],
                               searchList=[current_class, self])
                self.signature_name = str(tpl)
            tpl = Template(file=os.path.join(gen.target, "templates", "ifunction_overloaded.c"),
                           searchList=[current_class, self, {"this_method": self}])
            gen.impl_file.write(str(tpl))


def to_property_name(prefix, method_name):
    if not method_name:
        return None

    prefix_len = len(prefix)
    if prefix_len > 0:
        prefix = prefix.lower()
        method_name_lower = method_name.lower()
        if method_name_lower == prefix or not method_name_lower.startswith(prefix):
            return None

    lower_first_letters = ""
    i = prefix_len
    while True:
        first_letter = method_name[i:i + 1]
        lower_first_letter = first_letter.lower()
        if first_letter == lower_first_letter:
            break
        lower_first_letters += lower_first_letter
        i += 1
    lower_len = len(lower_first_letters)
    if 1 < lower_len < len(method_name) - prefix_len:
        lower_first_letters = lower_first_letters[:-1] + \
                              lower_first_letters[-1].upper()
    property_name = lower_first_letters + method_name[prefix_len + lower_len:]
    if property_name[0].isdigit():
        property_name = '_' + property_name
    return property_name


def all_methods(methods):
    ret = []
    for method in methods:
        if isinstance(method, NativeOverloadedFunction):
            ret += all_methods(method.implementations)
        else:
            ret.append(method)
    return ret


def underlined_typename(type_name):
    return re.sub(r"[^a-zA-Z0-9]", '_', type_name.replace("::", "_"))


def insert_method(m, to):
    if not to.has_key(m.registration_name):
        to[m.registration_name] = m
    else:
        previous_m = to[m.registration_name]
        if isinstance(previous_m, NativeOverloadedFunction):
            previous_m.append(m)
        else:
            to[m.registration_name] = NativeOverloadedFunction([previous_m, m])


class NativeClass(object):
    def __init__(self, cursor, generator, parse_if_not_listed):
        # the cursor to the implementation
        self.cursor = cursor
        self.base_parent = None
        self.parents = []
        self.fields = []
        self.public_fields = []
        self.methods = {}
        self.all_methods = {}
        self.private_constructors = []
        self.constructor = None
        self.has_default_constructor = False
        self.has_copy_constructor = False
        self.has_copy_operator = False
        self.static_methods = {}
        self.property_methods = []
        self.generator = generator
        self.pure_virtual_methods = []
        self.private_methods = []
        self.public_methods = []
        self._current_visibility = cindex.AccessSpecifier.PUBLIC \
            if cursor.kind == cindex.CursorKind.STRUCT_DECL else \
            cindex.AccessSpecifier.PRIVATE
        # for generate lua api doc
        self.override_methods = {}
        self.namespace_name = ""
        self.is_code_generated = False
        self.has_virtual_methods = False
        self.has_virtual_destructor = False
        self.is_destructor_private = False
        self.all_pure_virtual_methods = None

        self.namespaced_class_name = get_namespaced_name(cursor)
        self.namespace_name = get_namespace_name(cursor)
        self.class_name = self.namespaced_class_name[len(self.namespace_name):]

        self.is_base_class = self.class_name in generator.base_classes
        self.is_abstract = self.class_name in generator.abstract_classes

        registration_name = generator.get_class_or_rename_class(
            self.class_name, self.namespaced_class_name)

        underlined_class_name = underlined_typename(registration_name)
        self.qtscript_class_name = "QtScript" + underlined_class_name
        if generator.remove_prefix:
            self.target_class_name = re.sub('^' + generator.remove_prefix, '', registration_name)
        else:
            self.target_class_name = registration_name

        if parse_if_not_listed or generator.in_listed_classes(self):
            self.parse()
        else:
            self.is_parsed = False

    @property
    def namespace_name_no_suffix(self):
        if self.namespace_name.endswith('::'):
            return self.namespace_name[:-2]
        return self.namespace_name

    @property
    def namespace_list(self):
        if not self.namespace_name:
            return []

        return self.namespace_name_no_suffix.split('::')

    @property
    def underlined_class_name(self):
        return underlined_typename(self.namespaced_class_name)

    @property
    def root_base_parent(self):
        cls = self.base_parent
        while cls:
            if cls.base_parent is None:
                return cls
            cls = cls.base_parent
        return None

    def parse(self):
        '''
        parse the current cursor, getting all the necesary information
        '''
        self.is_parsed = True
        self._deep_iterate(self.cursor)
        self._init_property_methods()
        self.get_all_pure_virtual_methods()
        self._check_constructor()

    @property
    def is_default_constructable(self):
        return self.has_default_constructor and not self.is_abstract and not self.is_destructor_private

    @property
    def is_inplace_class(self):
        return (self.has_copy_constructor or self.has_copy_operator) and \
            not self.has_virtual_methods and self.is_default_constructable

    @property
    def has_base_parent(self):
        return self.base_parent is not None \
            and self.base_parent.has_virtual_destructor \
            and not self.is_inplace_class \
            and not self.base_parent.is_inplace_class

    def _check_constructor(self):
        self.has_default_constructor = True
        self.has_copy_constructor = True
        for c in self.private_constructors:
            self.has_default_constructor = False
            if not self.has_copy_constructor:
                break

            if c.is_copy_operator:
                self.has_copy_constructor = False
                if not self.has_default_constructor:
                    break

        self.has_copy_operator = True
        for m in self.private_methods:
            if m.is_copy_operator:
                self.has_copy_operator = False
                break

        for m in self.public_methods:
            if m.is_copy_operator:
                self.has_copy_operator = True
                break

        if self.constructor:
            self.has_default_constructor = False
            self.has_copy_constructor = False
            for impl in self.constructor.implementations if self.constructor.is_overloaded else [self.constructor]:
                if impl.real_min_args == 0:
                    self.has_default_constructor = True
                    if self.has_copy_constructor:
                        break

                if impl.is_copy_operator:
                    self.has_copy_constructor = True
                    if self.has_default_constructor:
                        break

    def get_all_pure_virtual_methods(self):
        if self.all_pure_virtual_methods is not None:
            return

        pure_virtual_methods = []
        for parent in self.parents:
            parent.get_all_pure_virtual_methods()
            for pure_m in parent.all_pure_virtual_methods:
                found = False
                if pure_m.registration_name in self.methods:
                    m = self.methods[pure_m.registration_name]
                    if isinstance(m, NativeOverloadedFunction):
                        for impl in m.implementations:
                            if impl.same_as(pure_m):
                                found = True
                                break
                    elif m.same_as(pure_m):
                        found = True

                if not found:
                    for m in self.private_methods:
                        if pure_m.registration_name == m.registration_name and m.same_as(pure_m):
                            found = True
                            break

                if not found:
                    pure_virtual_methods.append(pure_m)

        pure_virtual_methods += self.pure_virtual_methods
        if self.is_abstract or len(pure_virtual_methods) > 0:
            self.is_abstract = True
            self.constructor = None
        self.all_pure_virtual_methods = pure_virtual_methods

    def _init_property_methods(self):
        '''
        list of property methods
        '''
        self.property_methods = []
        if self.generator.script_type != "qtscript":
            return

        methods = all_methods(self.methods.itervalues())
        for impl in methods:
            if self.generator.should_skip_method(self, impl.registration_name):
                continue

            property_name = to_property_name('set', impl.registration_name)
            if property_name is None:
                continue

            if impl.ret_type.namespaced_name != "void" or impl.max_args == 0 or impl.min_args > 1:
                continue

            getter = None
            for getter_impl in methods:
                if getter_impl.registration_name == impl.registration_name:
                    continue

                if self.generator.should_skip_method(self, getter_impl.registration_name):
                    continue

                if getter_impl.min_args > 0:
                    continue

                if getter_impl.ret_type.namespaced_name != impl.arguments[0].namespaced_name:
                    continue

                getter_property_name = getter_impl.registration_name
                if getter_property_name != property_name:
                    getter_property_name = to_property_name('is', getter_impl.registration_name)
                    if getter_property_name is None:
                        getter_property_name = to_property_name('get', getter_impl.registration_name)
                    if getter_property_name is None:
                        continue

                if getter_property_name == property_name:
                    getter = getter_impl
                    break

            if getter is None:
                continue

            impl.is_property_method = True
            getter.is_property_method = True
            prop = {"name": property_name, "setter": impl, "getter": getter}
            self.property_methods.append(prop)

    def methods_clean(self):
        '''
        clean list of methods (without the ones that should be skipped)
        '''
        ret = []
        for name, impl in self.methods.iteritems():
            if self.generator.should_skip_method(self, name):
                continue

            ret.append({"name": name, "impl": impl})
        return sorted(ret, key=lambda entry: entry['name'])

    def static_methods_clean(self):
        '''
        clean list of static methods (without the ones that should be skipped)
        '''
        ret = []
        for name, impl in self.static_methods.iteritems():
            should_skip = self.generator.should_skip_method(self, name)
            if not should_skip:
                ret.append({"name": name, "impl": impl})
        return sorted(ret, key=lambda entry: entry['name'])

    def override_methods_clean(self):
        '''
        clean list of override methods (without the ones that should be skipped)
        '''
        ret = []
        for name, impl in self.override_methods.iteritems():
            should_skip = self.generator.should_skip_method(self, name)
            if not should_skip:
                ret.append({"name": name, "impl": impl})
        return ret

    def generate_qtproperty_declaration(self, entry):
        '''
        generate qtscript property declaration
        '''
        name = entry['name']
        getter = entry['getter'].registration_name
        if name.startswith('_') and getter.startswith('is'):
            name = 'is' + name[1:]
        self.generator.head_file.write(
            "\tQ_PROPERTY({type} {name} READ {getter} WRITE {setter})\n".format(
                type=entry['getter'].ret_type.to_string(self.generator),
                name=name,
                getter=getter,
                setter=entry['setter'].registration_name))

    def generate_code(self):
        '''
        actually generate the code. it uses the current target templates/rules in order to
        generate the right code
        '''

        assert (not self.is_code_generated)

        if not self.is_base_class:
            self.is_base_class = self._is_base_class()

        prelude_h = Template(file=os.path.join(self.generator.target, "templates", "prelude.h"),
                             searchList=[{"current_class": self}])
        prelude_c = Template(file=os.path.join(self.generator.target, "templates", "prelude.c"),
                             searchList=[{"current_class": self}])

        self.generator.head_file.write(str(prelude_h))
        self.generator.impl_file.write(str(prelude_c))

        for entry in self.property_methods_sorted():
            self.generate_qtproperty_declaration(entry)

        for m in self.methods_clean():
            m['impl'].generate_code(self)

        for m in self.static_methods_clean():
            m['impl'].generate_code(self)

        if self.constructor:
            self.constructor.generate_code(self)

        for m in self.public_fields_sorted():
            if self.generator.should_bind_field(self, m.name):
                m.generate_code(self)
        # generate register section
        register_h = Template(file=os.path.join(self.generator.target, "templates", "register.h"),
                              searchList=[{"current_class": self}])
        register_c = Template(file=os.path.join(self.generator.target, "templates", "register.c"),
                              searchList=[{"current_class": self}])
        # apidoc_classfoot_script = Template(file=os.path.join(self.generator.target,
        #                                                  "templates",
        #                                                  "apidoc_classfoot.script"),
        #                                searchList=[{"current_class": self}])
        self.generator.head_file.write(str(register_h))
        self.generator.impl_file.write(str(register_c))

        self.is_code_generated = True

        # self.generator.doc_file.write(str(apidoc_classfoot_script))
        # if self.generator.script_type == "lua":
        #     apidoc_fun_foot_script  = Template(file=os.path.join(self.generator.target,
        #                                                  "templates",
        #                                                  "apidoc_function_foot.script"),
        #                                searchList=[{"current_class": self}])
        #     self.doc_func_file.write(str(apidoc_fun_foot_script))
        #     self.doc_func_file.close()

    def public_fields_sorted(self):
        return sorted(self.public_fields, key=lambda field: field.name)

    def property_methods_sorted(self):
        return sorted(self.property_methods, key=lambda m: m['name'])

    def _deep_iterate(self, cursor=None):
        for node in cursor.get_children():
            self._process_node(node)

    def _is_base_class(self):
        """
        Mark the class as 'cocos2d::Ref' or its subclass.
        """
        if self.is_base_class:
            return True

        for parent in self.parents:
            if parent._is_base_class():
                return True

        return False

    def _process_node(self, cursor):
        if cursor.kind == cindex.CursorKind.CXX_BASE_SPECIFIER:
            parent = cursor.get_definition()
            parent_name = parent.displayname
            namespaced_parent_class_name = get_namespaced_name(parent) if parent_name else None

            if namespaced_parent_class_name and self.class_name not in self.generator.classes_have_no_parents and \
                    namespaced_parent_class_name not in self.generator.base_classes_to_skip:
                if not self.generator.generated_classes.has_key(namespaced_parent_class_name):
                    parent = NativeClass(parent, self.generator, parse_if_not_listed=True)
                    self.generator.generated_classes[namespaced_parent_class_name] = parent
                else:
                    parent = self.generator.generated_classes[namespaced_parent_class_name]

                if parent.has_virtual_methods:
                    self.has_virtual_methods = True

                if parent.has_virtual_destructor:
                    self.has_virtual_destructor = True

                if parent._is_base_class():
                    if not self.is_base_class or self.base_parent is None:
                        self.is_base_class = True
                        self.base_parent = parent
                elif self.base_parent is None:
                    self.base_parent = parent

                self.parents.append(parent)

        elif self._current_visibility == cindex.AccessSpecifier.PUBLIC and \
                (cursor.kind == cindex.CursorKind.CLASS_DECL or cursor.kind == cindex.CursorKind.STRUCT_DECL):
            self.generator.iterate_class(cursor)

        elif cursor.kind == cindex.CursorKind.FIELD_DECL:
            self.fields.append(NativeField(cursor))
            if self._current_visibility == cindex.AccessSpecifier.PUBLIC and NativeField.can_parse(cursor.type):
                self.public_fields.append(NativeField(cursor))

        elif cursor.kind == cindex.CursorKind.CXX_ACCESS_SPEC_DECL:
            self._current_visibility = cursor.access_specifier
            if self.generator.script_type == "qtscript":
                extent = cursor.extent
                start = extent.start.column
                end = extent.end.column
                count = (end - start) + 1
                if extent.start.line == extent.end.line and 8 <= count <= 11:
                    with open(extent.start.file.name, 'rb') as f:
                        f.seek(extent.start.offset)
                        content = unicode(f.read(count)).strip()
                        if content == 'Q_OBJECT' or content == 'Q_GADGET' or \
                                content == 'Q_SIGNALS:' or content == 'signals':
                            self._current_visibility = cindex.AccessSpecifier.PRIVATE

        elif cursor.kind == cindex.CursorKind.CXX_METHOD or cursor.kind == cindex.CursorKind.CONVERSION_FUNCTION:
            if cursor.is_virtual_method():
                self.has_virtual_methods = True

            if get_availability(cursor) == AvailabilityKind.DEPRECATED:
                return

            # skip if variadic
            if not cursor.type.is_function_variadic():
                m = NativeFunction(cursor, is_constructor=False, cls=self)

                if (self._current_visibility == cindex.AccessSpecifier.PUBLIC
                        or m.is_override):
                    insert_method(m, self.all_methods)
                if (self._current_visibility != cindex.AccessSpecifier.PUBLIC
                        or m.not_supported):
                    self.private_methods.append(m)
                else:
                    self.public_methods.append(m)

                if m.is_pure_virtual:
                    self.is_abstract = True
                    self.pure_virtual_methods.append(m)

                # bail if the function is not supported (at least one arg not supported)
                if m.not_supported:
                    return

                if self._current_visibility != cindex.AccessSpecifier.PUBLIC:
                    return

                if m.is_override:
                    if self.generator.script_type == "lua":
                        insert_method(m, self.override_methods)
                    return

                if m.static:
                    insert_method(m, self.static_methods)
                else:
                    insert_method(m, self.methods)

        elif cursor.kind == cindex.CursorKind.DESTRUCTOR:
            if cursor.is_virtual_method():
                self.has_virtual_methods = True
                self.has_virtual_destructor = True

            self.is_destructor_private = self._current_visibility != cindex.AccessSpecifier.PUBLIC

        elif cursor.kind == cindex.CursorKind.CONSTRUCTOR and not self.is_abstract:
            m = NativeFunction(cursor, is_constructor=True, cls=self)

            if not m.not_supported and self._current_visibility == cindex.AccessSpecifier.PUBLIC:
                if self.constructor is None:
                    self.constructor = m
                else:
                    previous_m = self.constructor
                    if isinstance(previous_m, NativeOverloadedFunction):
                        previous_m.append(m)
                    else:
                        m = NativeOverloadedFunction([previous_m, m])
                        m.is_constructor = True
                        self.constructor = m
            else:
                self.private_constructors.append(m)


def get_function_decl_with_params(k):
    k = k.strip()
    args = None
    ret_type = None
    native_args = None
    begin = k.find('(')
    end = 0
    func_name = ''
    if begin >= 0:
        end = k.find(')')
        assert end > begin
        func_name = k[:begin]
        if func_name == 'operator':
            func_name = 'operator()'
            begin = k.find('(', end)
            end = k.find(')', end)

    if begin >= 0:
        args = []
        s = k[begin + 1:end].strip()
        if s:
            for arg in s.split(","):
                t = arg.strip()
                args.append(None if t == '?' else NativeType.from_string(t))

        s = k[end + 1:].strip()
        ret_type = s.split(",")

        arg_count = len(ret_type)
        if arg_count > 1:
            native_args = ret_type[1:]

        k = func_name.strip()
        if arg_count > 0:
            ret_type = ret_type[0]

        ret_type = None if not ret_type or ret_type == '?' else NativeType.from_string(ret_type)

    return {
        'name': k,
        'args': args,
        'ret_type': ret_type,
        'native_args': native_args
    }


def get_children_array_from_iter(iter):
    children = []
    for child in iter:
        children.append(child)
    return children


class Generator(object):
    def __init__(self, opts):
        self.index = cindex.Index.create()
        self.outdir = opts['outdir']
        self.search_path = opts['search_path']
        self.prefix = opts['prefix']
        self.headers = opts['headers'].split(' ')
        self.classes = opts['classes']
        self.classes_have_no_parents = opts['classes_have_no_parents'].split(' ')
        self.base_classes_to_skip = opts['base_classes_to_skip'].split(' ')
        self.abstract_classes = opts['abstract_classes'].split(' ')
        self.clang_args = opts['clang_args']
        self.target = opts['target']
        self.remove_prefix = opts['remove_prefix']
        self.target_ns = opts['target_ns']
        self.cpp_ns = [ns if ns != '::' else '' for ns in opts['cpp_ns']]

        self.impl_file = None
        self.head_file = None
        self.skip_methods = {}
        self.skip_classes = []
        self.bind_fields = {}
        self.skip_fields = {}
        self.generated_classes = {}
        self.rename_functions = {}
        self.rename_classes = {}
        self.replace_headers = {}
        self.ignore_metatypes = []
        self.out_file = opts['out_file']
        self.script_control_cpp = opts['script_control_cpp'] == "yes"
        self.script_type = opts['script_type']
        self.macro_judgement = opts['macro_judgement']
        self.hpp_headers = opts['hpp_headers']
        self.cpp_headers = opts['cpp_headers']
        self.base_classes = opts['base_classes'].split(' ')
        self.win32_clang_flags = opts['win32_clang_flags']

        extend_clang_args = []

        for clang_arg in self.clang_args:
            if not os.path.exists(clang_arg.replace("-I", "")):
                pos = clang_arg.find("lib/clang/3.3/include")
                if -1 != pos:
                    extend_clang_arg = clang_arg.replace("3.3", "3.4")
                    if os.path.exists(extend_clang_arg.replace("-I", "")):
                        extend_clang_args.append(extend_clang_arg)

        if len(extend_clang_args) > 0:
            self.clang_args.extend(extend_clang_args)

        if sys.platform == 'win32' and self.win32_clang_flags != None:
            self.clang_args.extend(self.win32_clang_flags)

        if opts['skip_methods']:
            list_of_skips = re.split(";\n?", opts['skip_methods'])
            for skip in list_of_skips:
                pos = skip.find("@")
                if pos <= 0:
                    raise Exception("invalid list of skip_methods")

                class_name = skip[:pos].strip()
                list_of_methods = skip[pos + 1:].strip().split('#')
                self.skip_methods[class_name] = list_of_methods

                if len(list_of_methods) == 0:
                    raise Exception("no skip_methods for {}".format(class_name))

        if opts['skip_classes']:
            self.skip_classes = opts['skip_classes'].split()

        if opts['ignore_metatypes']:
            self.ignore_metatypes = opts['ignore_metatypes'].split()

        if opts['field']:
            list_of_fields = opts['field'].split(';')
            for field in list_of_fields:
                pos = field.find("@")
                if pos <= 0:
                    raise Exception("invalid list of fields")

                class_name = field[:pos].strip()
                list_of_fields = field[pos + 1:].strip().split('#')
                self.bind_fields[class_name] = list_of_fields

                if len(list_of_fields) == 0:
                    raise Exception("no fields to bind")

        if opts['skip_field']:
            list_of_fields = opts['skip_field'].split(';')
            for field in list_of_fields:
                pos = field.find("@")
                if pos <= 0:
                    raise Exception("invalid list of fields")

                class_name = field[:pos].strip()
                list_of_fields = field[pos + 1:].strip().split('#')
                self.skip_fields[class_name] = list_of_fields

                if len(list_of_fields) == 0:
                    raise Exception("no fields to skip")

        if opts['rename_functions']:
            list_of_function_renames = opts['rename_functions'].split(";")
            for rename in list_of_function_renames:
                pos = rename.find("@")
                if pos <= 0:
                    raise Exception("invalid list of rename methods")

                class_name = rename[:pos].strip()
                list_of_methods = rename[pos + 1:].strip().split('#')
                self.rename_functions[class_name] = {}
                if len(list_of_methods) == 0:
                    raise Exception("no methods to rename for {}".format(
                        class_name))
                for pair in list_of_methods:
                    split = pair.split("@")
                    if len(split) == 2:
                        k = split[0]
                        v = split[1]
                    else:
                        raise Exception(
                            "invalid list of rename methods "
                            "(should separate with @) for {}".format(class_name))

                    obj = get_function_decl_with_params(k)
                    obj['to'] = get_function_decl_with_params(v)

                    func_name = obj['name']
                    m = self.rename_functions[class_name]
                    if func_name not in m:
                        m[func_name] = []

                    m[func_name].append(obj)

        if opts['rename_classes']:
            list_of_class_renames = re.split(";\n?", opts['rename_classes'])
            for rename in list_of_class_renames:
                class_name, renamed_class_name = rename.split("@")
                self.rename_classes[class_name.strip()] = renamed_class_name.strip()

        if opts['replace_headers']:
            list_of_replace_headers = re.split(";\n?", opts['replace_headers'])
            for replace in list_of_replace_headers:
                header, replaced_header = replace.split("@")
                header = header.strip()
                replaced_header = replaced_header.strip()
                if not (replaced_header.startswith("<") and replaced_header.endswith(">")):
                    replaced_header = '"' + replaced_header + '"'
                self.replace_headers[header] = replaced_header

    def should_rename_function(self, cls, method_name):
        rename_sets = []
        for cls_re, map in self.rename_functions.iteritems():
            is_match = cls_re == '*'
            if not is_match:
                pattern = re.compile("^" + cls_re + "$")
                if pattern.match(cls.namespaced_class_name) \
                        or pattern.match(cls.class_name):
                    is_match = True
            if is_match and method_name in map:
                rename_sets.extend(map[method_name])
        return rename_sets

    def is_targeted_class(self, namespaced_class_name):
        if self.cpp_ns:
            for ns in self.cpp_ns:
                if not ns:
                    if '::' not in namespaced_class_name:
                        return True
                elif namespaced_class_name.startswith(ns + '::') and '::' not in namespaced_class_name[len(ns) + 2:]:
                    return True
            return False

        return True

    def get_class_or_rename_class(self, class_name, namespaced_class_name):
        if namespaced_class_name in self.rename_classes:
            class_name = self.rename_classes[namespaced_class_name]
        elif class_name in self.rename_classes:
            class_name = self.rename_classes[class_name]
        return underlined_typename(class_name)

    def should_skip_class(self, cls):
        for key in self.skip_classes:
            if not key:
                continue

            pattern = re.compile('^' + key + '$')
            if pattern.match(cls.namespaced_class_name) or pattern.match(
                    cls.class_name):
                return True

        return False

    def should_skip_method(self, cls, method_name):
        for key in self.skip_methods.iterkeys():
            is_match = key == '*'

            if not is_match:
                pattern = re.compile("^" + key + "$")
                if pattern.match(cls.namespaced_class_name) or pattern.match(
                    cls.class_name):
                    is_match = True

            if is_match:
                skip_methods = self.skip_methods[key]
                if len(skip_methods) == 1 and skip_methods[0] == "*":
                    return True

                for func in skip_methods:
                    if re.match("^" + func + "$", method_name):
                        return True
        return False

    def should_bind_field(self, cls, field_name):
        for key in self.skip_fields.iterkeys():
            is_match = key == '*'
            if not is_match:
                pattern = re.compile("^" + key + "$")
                if pattern.match(cls.namespaced_class_name) or pattern.match(
                        cls.class_name):
                    is_match = True

            if is_match:
                skip_fields = self.skip_fields[key]
                if len(skip_fields) == 1 and skip_fields[0] == "*":
                    return False
                if field_name is not None:
                    for field in skip_fields:
                        if re.match("^" + field + "$", field_name):
                            return False

        for key in self.bind_fields.iterkeys():
            is_match = key == '*'
            if not is_match:
                pattern = re.compile("^" + key + "$")
                if pattern.match(cls.namespaced_class_name) or pattern.match(
                        cls.class_name):
                    is_match = True

            if is_match:
                bind_fields = self.bind_fields[key]
                if len(bind_fields) == 1 and bind_fields[0] == "*":
                    return True
                if field_name is not None:
                    for field in bind_fields:
                        if re.match("^" + field + "$", field_name):
                            return True
        return False

    def in_listed_classes(self, cls):
        for key in self.classes:
            pattern = re.compile("^" + key + "$")
            md = pattern.match(cls.namespaced_class_name) or pattern.match(
                cls.class_name)
            if md and not self.should_skip_class(cls):
                return True
        return False

    def sorted_classes(self):
        class_list = []
        for nclass in self.generated_classes.itervalues():
            class_list += self._sorted_parents(nclass)

        return sorted(
            set(class_list), key=lambda nsclass: nsclass.namespaced_class_name)

    def _sorted_parents(self, nclass):
        '''
        returns the sorted list of parents for a native class
        '''
        sorted_parents = []
        for parent_class in nclass.parents:
            if self.generated_classes.has_key(parent_class.namespaced_class_name):
                sorted_parents += self._sorted_parents(parent_class)
        if self.generated_classes.has_key(nclass.namespaced_class_name):
            sorted_parents.append(nclass)
        return sorted_parents

    def generate_code(self):
        # must read the yaml file first
        stream = file(os.path.join(self.target, "conversions.yaml"), "r")
        data = yaml.load(stream)
        self.config = data
        implfilepath = os.path.join(self.outdir, self.out_file + ".cpp")
        headfilepath = os.path.join(self.outdir, self.out_file + ".hpp")

        # docfiledir   = self.outdir + "/api"
        # if not os.path.exists(docfiledir):
        #     os.makedirs(docfiledir)

        # if self.script_type == "lua":
        #     docfilepath = os.path.join(docfiledir, self.out_file + "_api.lua")
        # else:
        #     docfilepath = os.path.join(docfiledir, self.out_file + "_api.js")

        self.impl_file = open(implfilepath, "w+")
        self.head_file = open(headfilepath, "w+")
        # self.doc_file = open(docfilepath, "w+")

        layout_h = Template(file=os.path.join(self.target, "templates", "layout_head.h"),
                            searchList=[self])
        layout_c = Template(file=os.path.join(self.target, "templates", "layout_head.c"),
                            searchList=[self])
        # apidoc_ns_script = Template(file=os.path.join(self.target, "templates", "apidoc_ns.script"),
        #                         searchList=[self])
        self.head_file.write(str(layout_h))
        self.impl_file.write(str(layout_c))
        # self.doc_file.write(str(apidoc_ns_script))

        self._parse_headers()

        layout_h = Template(file=os.path.join(self.target, "templates", "layout_foot.h"),
                            searchList=[self])
        layout_c = Template(file=os.path.join(self.target, "templates", "layout_foot.c"),
                            searchList=[self])
        self.head_file.write(str(layout_h))
        self.impl_file.write(str(layout_c))
        # if self.script_type == "lua":
        #     apidoc_ns_foot_script = Template(file=os.path.join(self.target, "templates", "apidoc_ns_foot.script"),
        #                         searchList=[self])
        #     self.doc_file.write(str(apidoc_ns_foot_script))

        self.impl_file.close()
        self.head_file.close()
        # self.doc_file.close()

    def _pretty_print(self, diagnostics):
        errors = []
        for idx, d in enumerate(diagnostics):
            if d.severity > 2:
                errors.append(d)
        if len(errors) == 0:
            return
        print("====\nErrors in parsing headers:")
        severities = ['Ignored', 'Note', 'Warning', 'Error', 'Fatal']
        for idx, d in enumerate(errors):
            print "%s. <severity = %s,\n    location = %r,\n    details = %r>" % (
                idx + 1, severities[d.severity], d.location, d.spelling)
        print("====\n")

    def _parse_headers(self):
        for header in self.headers:
            tu = self.index.parse(header, self.clang_args)
            if len(tu.diagnostics) > 0:
                self._pretty_print(tu.diagnostics)
                is_fatal = False
                for d in tu.diagnostics:
                    if d.severity >= cindex.Diagnostic.Error:
                        is_fatal = True
                if is_fatal:
                    print("*** Found errors - can not continue")
                    raise Exception("Fatal error in parsing headers")
            self._deep_iterate(tu.cursor)

    def iterate_class(self, cursor):
        if cursor == cursor.type.get_declaration() and len(get_children_array_from_iter(cursor.get_children())) > 0:
            namespaced_class_name = get_namespaced_name(cursor)
            if cursor.displayname and self.is_targeted_class(namespaced_class_name):
                if not self.generated_classes.has_key(namespaced_class_name):
                    nclass = NativeClass(cursor, self, parse_if_not_listed=False)
                    if not nclass.is_parsed:
                        return False
                    nclass.generate_code()
                    self.generated_classes[namespaced_class_name] = nclass
                return True

        return False

    def _deep_iterate(self, cursor):
        # get the canonical type
        if cursor.kind == cindex.CursorKind.CLASS_DECL or cursor.kind == cindex.CursorKind.STRUCT_DECL:
            if self.iterate_class(cursor):
                return

        for node in cursor.get_children():
            self._deep_iterate(node)

    def scriptname_from_native(self, namespace_class_name, namespace_name):
        script_ns_dict = self.config['conversions']['ns_map']
        for (k, v) in script_ns_dict.items():
            if k == namespace_name:
                return namespace_class_name.replace("*", "").replace("const ", "").replace(k, v)
        if namespace_class_name.find("::") >= 0:
            if namespace_class_name.find("std::") == 0:
                return namespace_class_name
            else:
                raise Exception(
                    "The namespace (%s) conversion wasn't set in 'ns_map' section of the conversions.yaml" % namespace_class_name)
        else:
            return namespace_class_name.replace("*", "").replace("const ", "")

    def is_cocos_class(self, namespace_class_name):
        script_ns_dict = self.config['conversions']['ns_map']
        for (k, v) in script_ns_dict.items():
            if namespace_class_name.find("std::") == 0:
                return False
            if namespace_class_name.find(k) >= 0:
                return True

        return False

    def scriptname_cocos_class(self, namespace_class_name):
        script_ns_dict = self.config['conversions']['ns_map']
        for (k, v) in script_ns_dict.items():
            if namespace_class_name.find(k) >= 0:
                return namespace_class_name.replace("*", "").replace("const ", "").replace(k, v)
        raise Exception(
            "The namespace (%s) conversion wasn't set in 'ns_map' section of the conversions.yaml" % namespace_class_name)

    def js_typename_from_natve(self, namespace_class_name):
        script_ns_dict = self.config['conversions']['ns_map']
        if namespace_class_name.find("std::") == 0:
            if namespace_class_name.find("std::string") == 0:
                return "String"
            if namespace_class_name.find("std::vector") == 0:
                return "Array"
            if namespace_class_name.find("std::map") == 0 or namespace_class_name.find("std::unordered_map") == 0:
                return "map_object"
            if namespace_class_name.find("std::function") == 0:
                return "function"

        for (k, v) in script_ns_dict.items():
            if namespace_class_name.find(k) >= 0:
                if namespace_class_name.find("cocos2d::Vec2") == 0:
                    return "vec2_object"
                if namespace_class_name.find("cocos2d::Vec3") == 0:
                    return "vec3_object"
                if namespace_class_name.find("cocos2d::Vec4") == 0:
                    return "vec4_object"
                if namespace_class_name.find("cocos2d::Mat4") == 0:
                    return "mat4_object"
                if namespace_class_name.find("cocos2d::Vector") == 0:
                    return "Array"
                if namespace_class_name.find("cocos2d::Map") == 0:
                    return "map_object"
                if namespace_class_name.find("cocos2d::Point") == 0:
                    return "point_object"
                if namespace_class_name.find("cocos2d::Size") == 0:
                    return "size_object"
                if namespace_class_name.find("cocos2d::Rect") == 0:
                    return "rect_object"
                if namespace_class_name.find("cocos2d::Color3B") == 0:
                    return "color3b_object"
                if namespace_class_name.find("cocos2d::Color4B") == 0:
                    return "color4b_object"
                if namespace_class_name.find("cocos2d::Color4F") == 0:
                    return "color4f_object"
                else:
                    return namespace_class_name.replace("*", "").replace("const ", "").replace(k, v)
        return namespace_class_name.replace("*", "").replace("const ", "")

    def lua_typename_from_natve(self, namespace_class_name, is_ret=False):
        script_ns_dict = self.config['conversions']['ns_map']
        if namespace_class_name.find("std::") == 0:
            if namespace_class_name.find("std::string") == 0:
                return "string"
            if namespace_class_name.find("std::vector") == 0:
                return "array_table"
            if namespace_class_name.find("std::map") == 0 or namespace_class_name.find("std::unordered_map") == 0:
                return "map_table"
            if namespace_class_name.find("std::function") == 0:
                return "function"

        for (k, v) in script_ns_dict.items():
            if namespace_class_name.find(k) >= 0:
                if namespace_class_name.find("cocos2d::Vec2") == 0:
                    return "vec2_table"
                if namespace_class_name.find("cocos2d::Vec3") == 0:
                    return "vec3_table"
                if namespace_class_name.find("cocos2d::Vec4") == 0:
                    return "vec4_table"
                if namespace_class_name.find("cocos2d::Vector") == 0:
                    return "array_table"
                if namespace_class_name.find("cocos2d::Mat4") == 0:
                    return "mat4_table"
                if namespace_class_name.find("cocos2d::Map") == 0:
                    return "map_table"
                if namespace_class_name.find("cocos2d::Point") == 0:
                    return "point_table"
                if namespace_class_name.find("cocos2d::Size") == 0:
                    return "size_table"
                if namespace_class_name.find("cocos2d::Rect") == 0:
                    return "rect_table"
                if namespace_class_name.find("cocos2d::Color3B") == 0:
                    return "color3b_table"
                if namespace_class_name.find("cocos2d::Color4B") == 0:
                    return "color4b_table"
                if namespace_class_name.find("cocos2d::Color4F") == 0:
                    return "color4f_table"
                if is_ret == 1:
                    return namespace_class_name.replace("*", "").replace("const ", "").replace(k, "")
                else:
                    return namespace_class_name.replace("*", "").replace("const ", "").replace(k, v)
        return namespace_class_name.replace("*", "").replace("const ", "")

    # def api_param_name_from_native(self,native_name):
    #     lower_name = native_name.lower()
    #     if lower_name == "std::string" or lower_name == 'string' or lower_name == 'basic_string' or lower_name == 'std::basic_string':
    #         return "str"

    #     if lower_name.find("unsigned ") >= 0 :
    #         return native_name.replace("unsigned ","")

    #     if lower_name.find("unordered_map") >= 0 or lower_name.find("map") >= 0:
    #         return "map"

    #     if lower_name.find("vector") >= 0 :
    #         return "array"

    #     if lower_name == "std::function":
    #         return "func"
    #     else:
    #         return lower_name

    def js_ret_name_from_native(self, namespace_class_name, is_enum):
        if self.is_cocos_class(namespace_class_name):
            if namespace_class_name.find("cocos2d::Vector") >= 0:
                return "new Array()"
            if namespace_class_name.find("cocos2d::Map") >= 0:
                return "map_object"
            if is_enum:
                return 0
            else:
                return self.scriptname_cocos_class(namespace_class_name)

        lower_name = namespace_class_name.lower()

        if lower_name.find("unsigned ") >= 0:
            lower_name = lower_name.replace("unsigned ", "")

        if lower_name == "std::string":
            return ""

        if lower_name == "char" or lower_name == "short" or lower_name == "int" or lower_name == "float" or lower_name == "double" or lower_name == "long":
            return 0

        if lower_name == "bool":
            return "false"

        if lower_name.find("std::vector") >= 0 or lower_name.find("vector") >= 0:
            return "new Array()"

        if lower_name.find("std::map") >= 0 or lower_name.find("std::unordered_map") >= 0 or lower_name.find(
                "unordered_map") >= 0 or lower_name.find("map") >= 0:
            return "map_object"

        if lower_name == "std::function":
            return "func"
        else:
            return namespace_class_name


def main():
    from optparse import OptionParser

    parser = OptionParser("usage: %prog [options] {configfile}")
    parser.add_option("-s", action="store", type="string", dest="section",
                      help="sets a specific section to be converted")
    parser.add_option("-t", action="store", type="string", dest="target",
                      help="specifies the target vm. Will search for TARGET.yaml")
    parser.add_option("-o", action="store", type="string", dest="outdir",
                      help="specifies the output directory for generated C++ code")
    parser.add_option("-n", action="store", type="string", dest="out_file",
                      help="specifcies the name of the output file, defaults to the prefix in the .ini file")

    (opts, args) = parser.parse_args()

    # script directory
    workingdir = os.path.dirname(inspect.getfile(inspect.currentframe()))

    if len(args) == 0:
        parser.error('invalid number of arguments')

    userconfig = ConfigParser.SafeConfigParser(
        defaults={
            key: value
            for key, value in os.environ.iteritems()
        })
    userconfig.read('userconf.ini')
    print('Using userconfig:\n' + '\n'.join([
        "{} = {}".format(key, value)
        for key, value in userconfig.items('DEFAULT')
    ]))

    clang_lib_path = None
    if userconfig.has_option('DEFAULT', 'libclangdir'):
        clang_lib_path = os.path.abspath(
            userconfig.get('DEFAULT', 'libclangdir'))
    if clang_lib_path is None or not os.path.isdir(clang_lib_path):
        clang_lib_path = os.path.abspath(
            os.path.join(os.path.dirname(sys.argv[0]), 'libclang'))
    cindex.Config.set_library_path(clang_lib_path);

    config = ConfigParser.SafeConfigParser()
    config.set("DEFAULT", "current_dir", os.path.dirname(args[0]))
    config.read(args[0])

    if 0 == len(config.sections()):
        raise Exception("No sections defined in config file")

    sections = []
    if opts.section:
        if opts.section in config.sections():
            sections.append(opts.section)
        else:
            raise Exception("Section not found in config file")
    else:
        print("processing all sections")
        sections = config.sections()

    # find available targets
    targetdir = os.path.join(workingdir, "targets")
    targets = []
    if os.path.isdir(targetdir):
        targets = [
            entry
            for entry in os.listdir(targetdir)
            if not entry.startswith(".") and os.path.isdir(
                os.path.join(targetdir, entry))
        ]
    if 0 == len(targets):
        raise Exception("No targets defined")

    if opts.target:
        if opts.target in targets:
            targets = [opts.target]

    if opts.outdir:
        outdir = opts.outdir
    else:
        outdir = os.path.join(workingdir, "gen")
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    for t in targets:
        print "\n.... Generating bindings for target", t
        for s in sections:
            gen_opts = {
                'prefix': config.get(s, 'prefix'),
                'headers': (config.get(s, 'headers', 0, dict(userconfig.items('DEFAULT')))),
                'replace_headers': config.get(s, 'replace_headers') if config.has_option(s,
                                                                                         'replace_headers') else None,
                'ignore_metatypes': config.get(s, 'ignore_metatypes') if config.has_option(s,
                                                                                           'ignore_metatypes') else None,
                'classes': config.get(s, 'classes').split(' '),
                'clang_args': (config.get(s, 'extra_arguments', 0, dict(userconfig.items('DEFAULT'))) or "").split(" "),
                'target': os.path.join(workingdir, "targets", t),
                'outdir': outdir,
                'search_path': (config.get(s, 'search_path', 0, dict(userconfig.items('DEFAULT')))),
                'remove_prefix': config.get(s, 'remove_prefix'),
                'target_ns': config.get(s, 'target_namespace').split(' ') if config.has_option(s,
                                                                                               'cpp_namespace') else [],
                'cpp_ns': config.get(s, 'cpp_namespace').split(' ') if config.has_option(s, 'cpp_namespace') else [],
                'classes_have_no_parents': config.get(s, 'classes_have_no_parents'),
                'base_classes_to_skip': config.get(s, 'base_classes_to_skip'),
                'abstract_classes': config.get(s, 'abstract_classes'),
                'skip_methods': config.get(s, 'skip_methods') if config.has_option(s, 'skip_methods') else "",
                'skip_classes': config.get(s, 'skip_classes'),
                'field': config.get(s, 'field') if config.has_option(s, 'field') else None,
                'skip_field': config.get(s, 'skip_field') if config.has_option(s, 'skip_field') else "",
                'rename_functions': config.get(s, 'rename_functions', 0, dict(userconfig.items('DEFAULT'))),
                'rename_classes': config.get(s, 'rename_classes'),
                'out_file': opts.out_file or config.get(s, 'prefix'),
                'script_control_cpp': config.get(s, 'script_control_cpp') if config.has_option(s,
                                                                                               'script_control_cpp') else 'no',
                'script_type': t,
                'macro_judgement': config.get(s, 'macro_judgement') if config.has_option(s,
                                                                                         'macro_judgement') else None,
                'base_classes': config.get(s, 'base_classes') if config.has_option(s, 'base_classes') else "",
                'hpp_headers': config.get(s, 'hpp_headers', 0, dict(userconfig.items('DEFAULT'))).split(
                    ' ') if config.has_option(s, 'hpp_headers') else None,
                'cpp_headers': config.get(s, 'cpp_headers', 0, dict(userconfig.items('DEFAULT'))).split(
                    ' ') if config.has_option(s, 'cpp_headers') else None,
                'win32_clang_flags': (
                        config.get(s, 'win32_clang_flags', 0, dict(userconfig.items('DEFAULT'))) or "").split(
                    " ") if config.has_option(s, 'win32_clang_flags') else None
            }
            print "\n.... .... Processing section", s, "\n"
            generator = Generator(gen_opts)
            generator.generate_code()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

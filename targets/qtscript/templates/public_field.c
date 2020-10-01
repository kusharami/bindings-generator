#set ReturnType = $ntype.to_string($generator)
#if not $ntype.is_function
${ReturnType} ${qtscript_class_name}::_public_field_get_${pretty_name}() const
{
	auto object = thiz<${class_name} *>();
	if (object)
	{
#set in_value = 'object->' + $name;
#set ret_value = $ntype.from_native({
		"generator": $generator,
		"in_value": $in_value,
		"default": $in_value
	})
		return ${ret_value};
	}
#if $ReturnType == "bool"
	return false;
#elif $ReturnType.endswith('*')
	return nullptr;
#elif $ntype.is_enum or $ntype.is_numeric
	return static_cast<${ReturnType}>(0);
#else
	return ${ReturnType}();
#end if
}
#end if

#set arg_t = $ReturnType
#if $ntype.is_function
void ${qtscript_class_name}::set${pretty_name.capitalize()}(${arg_t} value)
#else
#if $ntype.is_object:
	#set $arg_t = 'const ' + $ReturnType + '&'
#end if
void ${qtscript_class_name}::_public_field_set_${pretty_name}(${arg_t} value)
#end if
{
#if $ntype.is_function
	auto __e = this->engine();
#end if
	auto object = thiz<${class_name} *>();
	if (object)
	{
		object->${name} = ${ntype.to_native({
						"generator": $generator,
						"arg": $ntype,
						"in_value": "value",
						"default": "value"
					})};
	}
}


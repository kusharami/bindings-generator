#set ReturnType = $ntype.to_string($generator)
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
#if $ntype.is_const and $ReturnType.endswith('*')
	#set $ret_value = 'const_cast<{}>({})'.format($ReturnType, $ret_value)
#end if
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

#set arg_t = $ReturnType
#if $ntype.is_object or $ntype.is_function:
	#set $arg_t = 'const ' + $ReturnType + '&'
#end if
void ${qtscript_class_name}::_public_field_set_${pretty_name}(${arg_t} value)
{
	auto object = thiz<${class_name} *>();
	if (object)
	{
		object->${name} = ${ntype.to_native({
						"generator": $generator,
						"is_const": $ntype.is_const,
						"in_value": "value",
						"default": "value"
					})};
	}
}


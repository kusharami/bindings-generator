#set ReturnType = $ret_type.namespaced_name
!${in_value}.isFunction() ? ${namespaced_name}() : [=](${lambda_parameters}) mutable#if $ReturnType != "void" # -> $ReturnType#end if #
{
#set ret_type_str = $ret_type.to_string($generator)
#set arg_idx = 0
#set arg_count = len($param_types)
	if (!${in_value}.engine()) {
#if $ret_type_str == "void"
		return;
#elif $ret_type_str == "bool"
		return false;
#elif $ret_type_str.endswith('*')
		return nullptr;
#elif $ret_type.is_enum or $ret_type.is_numeric
		return static_cast<${ret_type_str}>(0);
#else
		return ${ret_type_str}();
#end if
	}
	QScriptValueList arguments;
#while $arg_idx < $arg_count
	#set arg = $param_types[$arg_idx]
	#set arg_name = 'larg' + str($arg_idx)
	arguments << __e->toScriptValue(${arg.from_native({
				"generator": $generator,
				"in_value": $arg_name,
				"default": $arg_name
			})});
	#set $arg_idx += 1
#end while
#set from_qtscript = $in_value + '.call(QScriptValue(), arguments)'
#if $ReturnType == "void"
	${from_qtscript};
#else
	#if $ret_type_str != 'QScriptValue'
		#set $from_qtscript = "qscriptvalue_cast<{}>({})".format($ret_type_str, $from_qtscript)
	#end if
	return ${ret_type.to_native({
		"generator": $generator,
		"arg": $arg,
		"in_value": $from_qtscript,
		"default": $from_qtscript
	})};
#end if
}
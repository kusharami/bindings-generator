#set ReturnType = $ret_type.namespaced_name
!${in_value}.isFunction() ? ${namespaced_name}() : [=](${lambda_parameters}) mutable -> $ReturnType
{
#set arg_idx = 0
#set arg_count = len($param_types)
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
	#set ret_type_str = $ret_type.to_string($generator)
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
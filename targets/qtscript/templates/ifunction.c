#set ReturnType = $ret_type.to_string($generator)
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
	#set arg_decl_list = ", ".join($this_method.get_decl_arg_list($generator, $cur_min_args))
${ReturnType} ${signature_name}(${arg_decl_list})
{
	auto __o = this->thiz<${class_name} *>();
	#set arg_list = ", ".join($this_method.get_native_call_args($generator, $cur_min_args))
	#set call_method = "__o->{}({})".format($func_name, $arg_list)
	#if $ReturnType == "void"
	if (__o)
	{
		${call_method};
	}
	#else
	if (__o)
	{
		#set ret_value = $ret_type.from_native({
				"generator": $generator,
				"in_value": $call_method,
				"default": $call_method
			})
		#if $ret_type.is_const and $ReturnType.endswith('*')
			#set $ret_value = 'const_cast<{}>({})'.format($ReturnType, $ret_value)
		#end if
		return ${ret_value};
	}
		#if $ReturnType == "bool"
	return false;
		#elif $ReturnType.endswith('*')
	return nullptr;
		#elif $ret_type.is_enum or $ret_type.is_numeric
	return static_cast<${ReturnType}>(0);
		#else
	return ${ReturnType}();
		#end if
	#end if
}

	#set $cur_min_args += 1
#end while
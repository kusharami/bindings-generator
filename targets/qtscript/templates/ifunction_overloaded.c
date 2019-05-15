#if $base_parent is not None
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
	#for impl in $implementations
		#if $impl.static
			#continue
		#end if
		#if $cur_min_args < $impl.min_args or $cur_min_args > $impl.max_args
			#continue
		#end if
		#set ReturnType = $impl.ret_type.to_string($generator)
		#set arg_decl_list = ", ".join($impl.get_decl_arg_list($generator, $cur_min_args))
${ReturnType} ${signature_name}(${arg_decl_list})
{
	auto object = thiz<${class_name} *>();
		#set arg_list = ", ".join($impl.get_native_call_args($generator, $cur_min_args))
		#set call_method = "object->{}({})".format($func_name, $arg_list)
		#if $ReturnType == "void"
	if (object)
	{
		${call_method};
	}
		#else
	if (object)
	{
		#set ret_value = $impl.ret_type.from_native({
				"generator": $generator,
				"in_value": $call_method,
				"class_name": $class_name,
				"default": $call_method
			})
		#if $impl.ret_type.is_const and $ReturnType.endswith('*')
			#set $ret_value = 'const_cast<{}>({})'.format($ReturnType, $ret_value)
		#end if
		return ${ret_value};
	}
			#if $ReturnType == "bool"
	return false;
			#elif $ReturnType.endswith('*')
	return nullptr;
			#elif $impl.ret_type.is_enum
	return ${ReturnType}(0);
			#elif $impl.ret_type.is_numeric
	return 0;
			#else
	return ${ReturnType}();
			#end if
		#end if
}

	#end for
	#set $cur_min_args += 1
#end while
#end if
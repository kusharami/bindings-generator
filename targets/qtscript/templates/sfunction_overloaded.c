## ===== static function implementation template - for overloaded functions
QScriptValue ${signature_name}(QScriptContext *context, QScriptEngine* __e)
{
	if (!QtScriptUtils::checkArgumentCount(context, ${min_args}, ${max_args}))
	{
		return __e->uncaughtException();
	}

	switch (context->argumentCount())
	{
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
		case ${cur_min_args}:
		{
	#set implemented = False
	#for impl in $implementations
		#if not $impl.static
			#continue
		#end if
		#if $cur_min_args < $impl.min_args or $cur_min_args > $impl.max_args
			#continue
		#end if
		#set ReturnType = $impl.ret_type.to_string($generator)
		#set arg_list = []
		#if $cur_min_args > 0
			#set arg_idx = 0
			#while $arg_idx < $cur_min_args
				#set arg = $impl.arguments[$arg_idx]
				#set arg_type = $arg.to_string($generator)
				#set arg_name = 'arg' + str($arg_idx)
				#set arg_name_tmp = 'tmp_' + str($arg_idx)
				#if $arg_type == 'QScriptValue'
					#set from_qtscript = 'context->argument({})'.format($arg_idx)
				#else
					#set from_qtscript = "qscriptvalue_cast<{}>(context->argument({}))".format($arg_type, $arg_idx);
				#end if
				#set arg_native = $arg.to_native({
						"generator": $generator,
						"arg": $arg,
						"in_value": $arg_name_tmp,
						"default": $arg_name_tmp
					});
				#if $arg_native == $arg_name_tmp
			auto ${arg_name} = ${from_qtscript};
				#elif $arg_native == '*' + $arg_name_tmp
			auto ${arg_name} = ${from_qtscript};
			#set arg_name_dummy = 'dummy_' + str($arg_idx)
			${arg_decl[:-1]} ${arg_name_dummy};
			if (!${arg_name})
			{
				${arg_name} = &${arg_name_dummy};
			}
				#set arg_name = '*' + $arg_name
				#else
			auto ${arg_name_tmp} = ${from_qtscript};
			auto ${arg_name} = ${arg_native};
				#end if
				#set $arg_list += [$arg_name]
				#set $arg_idx += 1
			#end while
		#end if
		#set $arg_list = ", ".join($impl.get_native_call_args_with_list($arg_list));
		#set func_call = "{}::{}({})".format($class_name, $impl.func_name, $arg_list)
		#if $ReturnType == "void"
			${func_call};
			return __e->undefinedValue();
		#else
			return __e->toScriptValue(${impl.ret_type.from_native({
				"generator": $generator,
				"in_value": $func_call,
				"default": $func_call,
				"this_method": $impl
			})});
		#end if
		#set $implemented = True
		#break
	#end for
	#if not $implemented
			break;
	#end if
		}
	#set $cur_min_args += 1
#end while
	}

	QtScriptUtils::badArgumentsException(context,
			"${namespaced_class_name}::${func_name}");
	return __e->uncaughtException();
}


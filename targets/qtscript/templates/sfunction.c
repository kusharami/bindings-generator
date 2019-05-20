## ===== static function implementation template
QScriptValue ${signature_name}(QScriptContext *context, QScriptEngine* engine)
{
	if (!QtScriptEngineUtils::checkArgumentCount(context, ${min_args}, ${max_args}))
	{
		return engine->uncaughtException();
	}

	switch (context->argumentCount())
	{
#set cur_min_args = $min_args
#while $cur_min_args <= $max_args
		case ${cur_min_args}:
		{
	#set arg_list = []
	#set ReturnType = $ret_type.to_string($generator)
	#if $cur_min_args > 0
		#set arg_idx = 0
		#while $arg_idx < $cur_min_args
			#set arg = $arguments[$arg_idx]
			#set arg_name = 'arg' + str($arg_idx)
			#set arg_decl = $arg.to_string($generator)
			#set arg_name_tmp = 'tmp_' + str($arg_idx)
			#if $arg.namespaced_name == 'QScriptValue'
				#set from_qtscript = 'context->argument({})'.format($arg_idx)
			#else
				#set from_qtscript = "qscriptvalue_cast<{}>(context->argument({}))".format($arg_decl, $arg_idx);
			#end if
			#set arg_native = $arg.to_native({
					"generator": $generator,
					"is_const": $arg.is_const,
					"in_value": $arg_name_tmp,
					"default": $arg_name_tmp
				});
			#if $arg_native == $arg_name_tmp
			auto ${arg_name} = ${from_qtscript};
			#else
			auto ${arg_name_tmp} = ${from_qtscript};
			auto ${arg_name} = ${arg_native};
			#end if
			#set $arg_list += [$arg_name]
			#set $arg_idx += 1
		#end while
	#end if
	#set $arg_list = ", ".join($this_method.get_native_call_args_with_list($arg_list));
	#set func_call = "{}::{}({})".format($class_name, $func_name, $arg_list)
	#if $ReturnType == "void"
			${func_call};
			return engine->undefinedValue();
	#else
			return engine->toScriptValue(${ret_type.from_native({
				"generator": $generator,
				"in_value": $func_call,
				"default": $func_call
			})});
	#end if
		}
	#set $cur_min_args += 1
#end while
	}

	QtScriptEngineUtils::badArgumentsException(context,
			"${namespaced_class_name}::${func_name}");
	return engine->uncaughtException();
}


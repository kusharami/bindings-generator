};
#for namespace_name in reversed($current_class.namespace_list)

} // end of ${namespace_name}
#end for

#set ClassName = $current_class.namespaced_class_name
#set has_base_parent = $current_class.base_parent is not None and \
	not $current_class.is_inplace_class and \
	$current_class.is_inplace_class == $current_class.base_parent.is_inplace_class
#if not $has_base_parent
	#if not $current_class.is_inplace_class and not $current_class.is_base_class and not $current_class.is_destructor_private
	#set StorageType = $current_class.namespace_name + $current_class.qtscript_class_name + '::StorageType'
Q_DECLARE_METATYPE(${StorageType})
	#elif $current_class.is_inplace_class and $ClassName not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName})
	#end if
#end if
#if $ClassName + '*' not in $current_class.generator.ignore_metatypes
Q_DECLARE_METATYPE(${ClassName} *)
Q_DECLARE_METATYPE(const ${ClassName} *)
#end if


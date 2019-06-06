};
#for namespace_name in $current_class.namespace_list

} // end of ${namespace_name}
#end for

#if  $current_class.is_inplace_class
Q_DECLARE_METATYPE(${current_class.namespaced_class_name})
#end if
Q_DECLARE_METATYPE(${current_class.namespaced_class_name} *)

